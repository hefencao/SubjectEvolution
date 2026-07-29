#!/usr/bin/env python3
"""Fail before installation when project and package version sources diverge."""
from __future__ import annotations
import argparse, ast, json, tomllib
from pathlib import Path


def package_version(path: Path) -> str:
    tree = ast.parse(path.read_text(encoding='utf-8'))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == '__version__':
                    value = ast.literal_eval(node.value)
                    if isinstance(value, str):
                        return value
    raise RuntimeError(f'__version__ not found in {path}')


def check(project: Path) -> dict[str, object]:
    project = project.resolve()
    pyproject = tomllib.loads((project/'pyproject.toml').read_text(encoding='utf-8'))
    project_version = str(pyproject['project']['version'])
    package = package_version(project/'src/se/__init__.py')
    expected_docs = '.'.join(project_version.split('.')[:2])
    docs_dir = project / 'docs' / f'v{expected_docs}'
    if package != project_version or not docs_dir.is_dir():
        raise RuntimeError(
            f'version mismatch: pyproject={project_version}, package={package}, '
            f'docs_dir={docs_dir.relative_to(project)}, docs_exists={docs_dir.is_dir()}'
        )
    return {'passed': True, 'version': project_version, 'docs_version': expected_docs}


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument('--project', default='.')
    parser.add_argument('--report')
    args=parser.parse_args()
    report=check(Path(args.project))
    text=json.dumps(report, ensure_ascii=False, indent=2)
    if args.report:
        Path(args.report).write_text(text+'\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))

if __name__=='__main__':
    main()
