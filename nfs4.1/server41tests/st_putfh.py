from xdrdef.nfs4_const import *
from .environment import check, fail, use_obj, create_confirm, close_file
import nfs_ops
import struct
op = nfs_ops.NFS4ops()

def _try_put(t, sess, path):
    # Get fh via LOOKUP
    res = sess.compound(use_obj(path) + [op.getfh()])
    check(res)
    oldfh = res.resarray[-1].object
    # Now try PUTFH and GETFH, see if it agrees
    res = sess.compound([op.putfh(oldfh), op.getfh()])
    check(res)
    newfh = res.resarray[-1].object
    if oldfh != newfh:
        t.fail("GETFH did not return input of PUTFH for /%s" % '/'.join(path))

def testFile(t, env):
    """PUTFH followed by GETFH should end up with original fh

    FLAGS: putfh getfh lookup file all
    CODE: PUTFH1r
    """
    c = env.c1.new_client(env.testname(t))
    sess = c.create_session()
    _try_put(t, sess, env.opts.usefile)

def testLink(t, env):
    """PUTFH followed by GETFH should end up with original fh

    FLAGS: putfh getfh lookup symlink all
    CODE: PUTFH1a
    """
    c = env.c1.new_client(env.testname(t))
    sess = c.create_session()
    _try_put(t, sess, env.opts.uselink)

def testBlock(t, env):
    """PUTFH followed by GETFH should end up with original fh

    FLAGS: putfh getfh lookup block all
    CODE: PUTFH1b
    """
    c = env.c1.new_client(env.testname(t))
    sess = c.create_session()
    _try_put(t, sess, env.opts.useblock)

def testChar(t, env):
    """PUTFH followed by GETFH should end up with original fh

    FLAGS: putfh getfh lookup char all
    CODE: PUTFH1c
    """
    c = env.c1.new_client(env.testname(t))
    sess = c.create_session()
    _try_put(t, sess, env.opts.usechar)

def testDir(t, env):
    """PUTFH followed by GETFH should end up with original fh

    FLAGS: putfh getfh lookup dir all
    CODE: PUTFH1d
    """
    c = env.c1.new_client(env.testname(t))
    sess = c.create_session()
    _try_put(t, sess, env.opts.usedir)

def testFifo(t, env):
    """PUTFH followed by GETFH should end up with original fh

    FLAGS: putfh getfh lookup fifo all
    CODE: PUTFH1f
    """
    c = env.c1.new_client(env.testname(t))
    sess = c.create_session()
    _try_put(t, sess, env.opts.usefifo)

def testSocket(t, env):
    """PUTFH followed by GETFH should end up with original fh

    FLAGS: putfh getfh lookup socket all
    CODE: PUTFH1s
    """
    c = env.c1.new_client(env.testname(t))
    sess = c.create_session()
    _try_put(t, sess, env.opts.usesocket)

def testBadHandle(t, env):
    """PUTFH with bad filehandle should return NFS4ERR_BADHANDLE

    FLAGS: putfh all
    CODE: PUTFH2
    """
    c = env.c1.new_client(env.testname(t))
    sess = c.create_session()
    res = sess.compound([op.putfh(b'abc')])
    check(res, NFS4ERR_BADHANDLE, "PUTFH with bad filehandle='abc'")

def _illumos_handle(data_len, export_len, byteorder):
    # Internal lengths use the server's native byte order, unlike outer XDR.
    # Each data field occupies at least 10 bytes on the wire. Include all
    # declared bytes so rejection tests the 26-byte bound, not truncation.
    fh = (b'\0' * 8 + struct.pack(byteorder + 'H', data_len) +
          b'\0' * max(10, data_len) +
          struct.pack(byteorder + 'H', export_len) +
          b'\0' * max(10, export_len))
    # Align the trailing flags to four bytes within the opaque handle.
    return fh + b'\0' * (-len(fh) % 4) + b'\0' * 4

def _try_oversized_handle(t, env, data_len, export_len):
    c = env.c1.new_client(env.testname(t))
    sess = c.create_session()
    res = sess.compound(use_obj(env.opts.usefile) + [op.getfh()])
    check(res)
    goodfh = res.resarray[-1].object

    # Exercise both server byte orders without assuming the client's matches.
    for byteorder in ('<', '>'):
        badfh = _illumos_handle(data_len, export_len, byteorder)
        res = sess.compound([op.putfh(badfh), op.getfh()])
        check(res, NFS4ERR_BADHANDLE,
              "PUTFH with internal lengths %d/%d, byte order %s" %
              (data_len, export_len, byteorder))
        if len(res.resarray) != 1 or res.resarray[0].resop != OP_PUTFH:
            t.fail("Compound should stop at the rejected PUTFH")

        res = sess.compound([op.putfh(goodfh), op.getfh()])
        check(res, msg="Valid PUTFH after rejecting oversized internal length")
        if res.resarray[-1].object != goodfh:
            t.fail("GETFH did not return the valid handle after rejection")

def testOversizedDataLength(t, env):
    """Reject an illumos filehandle with internal data length above 26

    Uses the illumos opaque filehandle format and inert data. The overall
    handle is 56 bytes, with complete fields and trailing flags.

    FLAGS: putfh illumos
    CODE: PUTFH3
    """
    _try_oversized_handle(t, env, 27, 10)

def testOversizedExportLength(t, env):
    """Reject an illumos filehandle with internal export-data length above 26

    Uses the illumos opaque filehandle format and inert data. The overall
    handle is 56 bytes, with complete fields and trailing flags.

    FLAGS: putfh illumos
    CODE: PUTFH4
    """
    _try_oversized_handle(t, env, 10, 27)
