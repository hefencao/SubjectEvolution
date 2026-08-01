from pathlib import Path

root = Path(__file__).resolve().parents[1]
package = root / "src/subject_evolution"
files = sorted(package.rglob("*.py"))
assert files, "subject_evolution source package is missing"
for path in files:
    source = path.read_text(encoding="utf-8")
    compile(source, str(path), "exec")
print(f"subject_evolution syntax: ok ({len(files)} files)")
