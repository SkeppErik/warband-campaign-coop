"""Pure helpers that rewrite native operation blocks (docs/encounters.md). No module system imports, so the tests
can use them; the caller passes the opcodes.

An operation is an int (no arguments) or a tuple (opcode, args...); blocks can nest lists only as values.
"""

MODIFIER_MASK = 0xF0000000   # neg, this_or_next

try:
    INTEGERS = (int, long)   # Python 2: an opcode with a modifier bit is a long
except NameError:
    INTEGERS = (int,)


def op_code(op):
    if isinstance(op, (tuple, list)):
        return op[0] if op else None
    return op


def op_args(op):
    return list(op[1:]) if isinstance(op, (tuple, list)) else []


def rewrite_block(block, replace_ops, rename_args, call_script, expand_ops=None):
    """Returns a new block: an op whose plain opcode (no modifiers) is in replace_ops becomes
    (call_script, replace_ops[code](len(args)), *args); one in expand_ops becomes the ops expand_ops[code](args)
    returns (for operations that write a destination, which can't go through call_script); string arguments found
    in rename_args are renamed."""
    expand_ops = expand_ops or {}
    out = []
    for op in block:
        code = op_code(op)
        args = [rename_args.get(a, a) if isinstance(a, str) else a for a in op_args(op)]
        if isinstance(code, INTEGERS) and not (code & MODIFIER_MASK) and code in expand_ops:
            out.extend(expand_ops[code](args))
        elif isinstance(code, INTEGERS) and not (code & MODIFIER_MASK) and code in replace_ops:
            out.append(tuple([call_script, replace_ops[code](len(args))] + args))
        elif isinstance(op, (tuple, list)):
            out.append(tuple([code] + args))
        else:
            out.append(op)
    return out


def written_globals(block, writes_first_arg):
    """Global variables ("$name") a block writes: the first argument of the opcodes in writes_first_arg."""
    found = []
    for op in block:
        code = op_code(op)
        if isinstance(code, INTEGERS):
            code = int(code & ~MODIFIER_MASK & 0xFFFFFFFF)
        args = op_args(op)
        if code in writes_first_arg and args and isinstance(args[0], str) and args[0].startswith("$"):
            name = args[0][1:]
            if name not in found:
                found.append(name)
    return found
