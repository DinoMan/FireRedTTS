"""Patch fairseq for Python 3.11+ compatibility (mutable dataclass defaults).

This patches the installed fairseq package files in-place on first run.
"""
import sys
import os
import re
import glob


def patch():
    """Patch installed fairseq files to fix mutable dataclass defaults."""
    if sys.version_info < (3, 11):
        return

    # Find fairseq install location
    try:
        import fairseq
        fairseq_dir = os.path.dirname(fairseq.__file__)
    except (ImportError, ValueError):
        # fairseq can't even import yet - find it manually
        for p in sys.path:
            candidate = os.path.join(p, "fairseq")
            if os.path.isdir(candidate) and os.path.exists(os.path.join(candidate, "__init__.py")):
                fairseq_dir = candidate
                break
        else:
            return

    marker = os.path.join(fairseq_dir, ".patched_py311")
    if os.path.exists(marker):
        return

    # Patch 1: Replace mutable defaults  X() -> field(default_factory=X)
    # Matches: name: SomeType = SomeType()
    pattern = re.compile(r'(\w+:\s+)(\w+)\s*=\s*\2\(\)')
    field_default_pattern = re.compile(r'field\(default=(\w+)\(\)\)')

    # Patch fairseq and hydra
    dirs_to_patch = [fairseq_dir]
    for p in sys.path:
        hydra_dir = os.path.join(p, "hydra")
        if os.path.isdir(hydra_dir):
            dirs_to_patch.append(hydra_dir)
            break

    for patch_dir in dirs_to_patch:
        for pyfile in glob.glob(os.path.join(patch_dir, "**", "*.py"), recursive=True):
            try:
                with open(pyfile, 'r') as f:
                    content = f.read()
            except (IOError, UnicodeDecodeError):
                continue

            new_content = pattern.sub(r'\1\2 = field(default_factory=\2)', content)
            new_content = field_default_pattern.sub(r'field(default_factory=\1)', new_content)

            if new_content != content:
                with open(pyfile, 'w') as f:
                    f.write(new_content)

    # Patch 2: Skip hydra_init() in __init__.py
    init_path = os.path.join(fairseq_dir, "__init__.py")
    if os.path.exists(init_path):
        with open(init_path, 'r') as f:
            content = f.read()
        content = content.replace(
            "from fairseq.dataclass.initialize import hydra_init",
            "pass  # from fairseq.dataclass.initialize import hydra_init"
        )
        content = content.replace("hydra_init()", "pass  # hydra_init()")
        with open(init_path, 'w') as f:
            f.write(content)

    # Write marker
    with open(marker, 'w') as f:
        f.write("patched")
