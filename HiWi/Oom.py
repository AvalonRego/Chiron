# file: scripts/check_exit_codes.py
from pathlib import Path
import re
import argparse
from typing import Dict, List, Tuple

ExitRecord = Tuple[str, str, str]  # (jobid, exitcode, raw_line)

def parse_file_for_failed_jobs(path: Path) -> List[ExitRecord]:
    failed: List[ExitRecord] = []
    job_row_re = re.compile(r'^\s*\d')
    exitcode_re = re.compile(r'^\d+:\d+$')

    try:
        with path.open('r', errors='replace') as fh:
            for raw in fh:
                line = raw.rstrip('\n')
                if not line or line.strip().startswith('---'):
                    continue
                if 'JobID' in line and 'ExitCode' in line:
                    continue
                if not job_row_re.match(line):
                    continue

                tokens = re.split(r'\s+', line.strip())
                exitcode_token = None
                for tok in reversed(tokens):
                    if exitcode_re.match(tok):
                        exitcode_token = tok
                        break
                if not exitcode_token:
                    continue

                jobid = tokens[0] if tokens else ''
                if exitcode_token != '0:0':
                    failed.append((jobid, exitcode_token, line))
    except Exception:
        pass

    return failed

def find_failed_jobs(directory: str, recursive: bool = False) -> Dict[str, List[ExitRecord]]:
    base = Path(directory)
    if not base.exists() or not base.is_dir():
        raise FileNotFoundError(f"Directory not found: {directory}")

    results: Dict[str, List[ExitRecord]] = {}

    iterator = base.rglob('*') if recursive else base.iterdir()
    for p in iterator:
        if not p.is_file():
            continue
        failed = parse_file_for_failed_jobs(p)
        if failed:
            results[str(p)] = failed

    return results

def main():
    ap = argparse.ArgumentParser(description="Find files with non-zero Slurm ExitCode in job output files.")
    ap.add_argument('directory', help='Directory containing output files')
    ap.add_argument('-r', '--recursive', action='store_true', help='Scan subdirectories recursively')
    ap.add_argument('-d', '--details', action='store_true', help='Show job details (jobid and exit code)')
    args = ap.parse_args()

    try:
        bad = find_failed_jobs(args.directory, recursive=args.recursive)
    except FileNotFoundError as e:
        print(e)
        return

    if not bad:
        print("No files with non-zero ExitCode found.")
        return

    print("Files with non-zero ExitCode (sorted):")
    for fname in sorted(bad.keys()):
        print(f"- {fname}")
        if args.details:
            for jobid, code, raw in bad[fname]:
                print(f"    {jobid}  ExitCode={code}  | {raw}")

if __name__ == '__main__':
    main()

