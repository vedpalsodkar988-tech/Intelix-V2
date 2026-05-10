import subprocess
import os
import shutil
import time
from datetime import datetime
from ai_analyzer import analyze_results
import json

RUNS_FILE = 'runs.json'
WORKDIR = 'workspaces'

os.makedirs(WORKDIR, exist_ok=True)

def load_runs():
    if os.path.exists(RUNS_FILE):
        with open(RUNS_FILE, 'r') as f:
            return json.load(f)
    return []

def save_runs(runs):
    with open(RUNS_FILE, 'w') as f:
        json.dump(runs, f)

def update_run(run_id, status, report=None):
    runs = load_runs()
    for run in runs:
        if run['id'] == run_id:
            run['status'] = status
            if report:
                run['report'] = report
            break
    save_runs(runs)

class Executor:
    def run(self, run_id, repo_url, task_type, custom_command):
        print(f"\n🚀 Starting run {run_id}")
        workspace = os.path.join(WORKDIR, run_id)
        results = {
            'run_id': run_id,
            'repo_url': repo_url,
            'task_type': task_type,
            'started_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'steps': {}
        }

        print(f"📥 Cloning repo: {repo_url}")
        clone_result = self.clone_repo(repo_url, workspace)
        results['steps']['clone'] = clone_result
        if not clone_result['success']:
            print(f"❌ Clone failed: {clone_result['output']}")
            report = analyze_results(results)
            update_run(run_id, 'completed', report)
            return
        print("✅ Repo cloned")

        language = self.detect_language(workspace)
        results['language'] = language
        print(f"🔍 Detected language: {language}")

        print("📦 Installing dependencies...")
        install_result = self.install_dependencies(workspace, language)
        results['steps']['install'] = install_result
        if install_result['success']:
            print("✅ Dependencies installed")
        else:
            print(f"⚠️ Install issues: {install_result['output'][:200]}")

        print(f"⚡ Running task: {task_type}")
        start_time = time.time()
        task_result = self.run_task(workspace, language, task_type, custom_command)
        execution_time = round(time.time() - start_time, 2)
        results['steps']['task'] = task_result
        results['execution_time'] = execution_time
        print(f"✅ Task completed in {execution_time}s")

        self.cleanup(workspace)

        print("🧠 AI analyzing results...")
        report = analyze_results(results)
        update_run(run_id, 'completed', report)
        print(f"✅ Run {run_id} complete!")

    def clone_repo(self, repo_url, workspace):
        try:
            result = subprocess.run(
                f'git clone {repo_url} "{workspace}"',
                capture_output=True, text=True, timeout=120,
                shell=True
            )
            if result.returncode == 0:
                return {'success': True, 'output': 'Repository cloned successfully'}
            else:
                return {'success': False, 'output': result.stderr or result.stdout}
        except Exception as e:
            return {'success': False, 'output': str(e)}

    def detect_language(self, workspace):
        if os.path.exists(os.path.join(workspace, 'package.json')):
            return 'node'
        elif (
            os.path.exists(os.path.join(workspace, 'requirements.txt')) or
            os.path.exists(os.path.join(workspace, 'setup.py')) or
            os.path.exists(os.path.join(workspace, 'pyproject.toml')) or
            os.path.exists(os.path.join(workspace, 'setup.cfg')) or
            len([f for f in os.listdir(workspace) if f.endswith('.py')]) > 0
        ):
            return 'python'
        return 'unknown'

    def install_dependencies(self, workspace, language):
        try:
            if language == 'node':
                result = subprocess.run(
                    'npm install',
                    cwd=workspace,
                    capture_output=True, text=True, timeout=180,
                    shell=True
                )
            elif language == 'python':
                req_file = os.path.join(workspace, 'requirements.txt')
                if os.path.exists(req_file):
                    result = subprocess.run(
                        'py -m pip install -r requirements.txt',
                        cwd=workspace,
                        capture_output=True, text=True, timeout=180,
                        shell=True
                    )
                elif os.path.exists(os.path.join(workspace, 'pyproject.toml')):
                    result = subprocess.run(
                        'py -m pip install -e ".[dev,test]" || py -m pip install -e .',
                        cwd=workspace,
                        capture_output=True, text=True, timeout=180,
                        shell=True
                    )
                elif os.path.exists(os.path.join(workspace, 'setup.py')):
                    result = subprocess.run(
                        'py -m pip install -e .',
                        cwd=workspace,
                        capture_output=True, text=True, timeout=180,
                        shell=True
                    )
                else:
                    return {'success': True, 'output': 'No requirements file found'}
            else:
                return {'success': True, 'output': 'Unknown language, skipping install'}

            return {
                'success': result.returncode == 0,
                'output': (result.stdout + result.stderr)[-1000:]
            }
        except Exception as e:
            return {'success': False, 'output': str(e)}

    def run_task(self, workspace, language, task_type, custom_command):
        try:
            if custom_command:
                cmd = custom_command
            elif task_type == 'test':
                if language == 'node':
                    cmd = 'npm test'
                elif language == 'python':
                    cmd = 'py -m pip install pytest pytest-cov && py -m pytest --cache-clear'
                else:
                    cmd = 'echo No test command found'
            elif task_type == 'build':
                if language == 'node':
                    cmd = 'npm run build'
                elif language == 'python':
                    cmd = 'py setup.py build'
                else:
                    cmd = 'echo No build command found'
            else:
                cmd = custom_command or 'echo No command specified'

            result = subprocess.run(
                cmd,
                cwd=workspace,
                capture_output=True, text=True,
                timeout=300,
                shell=True
            )

            return {
                'success': result.returncode == 0,
                'output': (result.stdout + result.stderr)[-3000:],
                'return_code': result.returncode,
                'command': cmd
            }
        except subprocess.TimeoutExpired:
            return {'success': False, 'output': 'Task timed out after 5 minutes', 'return_code': -1, 'command': cmd}
        except Exception as e:
            return {'success': False, 'output': str(e), 'return_code': -1, 'command': ''}

    def cleanup(self, workspace):
        try:
            if os.path.exists(workspace):
                shutil.rmtree(workspace)
                print(f"🧹 Cleaned up workspace")
        except Exception as e:
            print(f"⚠️ Cleanup failed: {e}")