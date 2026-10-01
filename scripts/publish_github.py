"""Explicit publishing command: create a PRIVATE repository and push this project."""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OWNER='WitsawawitS'
REPO='ai-procurement-assistant'

def run(*args,capture=False):
    return subprocess.run(args,cwd=ROOT,check=True,text=True,capture_output=capture)

if __name__=='__main__':
    for executable in ('git','gh'):
        if not shutil.which(executable):
            sys.exit(f'Install {executable} first, then run this script again.')
    try:
        login=run('gh','api','user','--jq','.login',capture=True).stdout.strip()
        if login.lower()!=OWNER.lower():
            sys.exit(f'Expected {OWNER}, but GitHub CLI is signed in as {login}. Run gh auth switch or gh auth login.')
        existing=subprocess.run(['gh','repo','view',f'{OWNER}/{REPO}'],cwd=ROOT,capture_output=True)
        if existing.returncode==0:
            sys.exit('Repository already exists. Stop to avoid overwriting work; use GitHub Desktop or review its contents before pushing.')
        if (ROOT/'.git').exists():
            remotes=run('git','remote',capture=True).stdout.split()
            if 'origin' in remotes:
                sys.exit('An origin remote already exists. Review it before publishing; this helper will not replace it.')
        run(sys.executable,'-m','unittest','discover','-v')
        if not (ROOT/'.git').exists():run('git','init','-b','main')
        # Uses your own Git configuration. Never invent a commit identity.
        if subprocess.run(['git','var','GIT_AUTHOR_IDENT'],cwd=ROOT,capture_output=True).returncode:
            sys.exit('Set your Git user.name and user.email first. See GitHub Desktop setup or Git documentation.')
        run('git','add','README.md','LICENSE','.gitignore','.env.example','START_WINDOWS.bat','app.py','procurement','web','data','tests','docs','scripts','.github')
        if subprocess.run(['git','diff','--cached','--quiet'],cwd=ROOT).returncode:
            run('git','commit','-m','Build explainable AI procurement portfolio application')
        run('gh','repo','create',f'{OWNER}/{REPO}','--private','--source=.','--remote=origin','--push',
            '--description','Explainable supplier comparison, landed cost and scenario analysis with Python, SQLite and optional AI.')
        print(f'Published: https://github.com/{OWNER}/{REPO}')
    except subprocess.CalledProcessError:
        sys.exit('Publishing stopped. Review the error above; no force push or remote overwrite was attempted.')
