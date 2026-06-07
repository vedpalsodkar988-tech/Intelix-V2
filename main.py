import ddtrace
ddtrace.patch_all()

from flask import Flask, render_template, request, jsonify
import json
import os
from datetime import datetime
import threading

app = Flask(__name__)
RUNS_FILE = 'runs.json'

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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/history')
def history():
    return render_template('history.html')

@app.route('/settings')
def settings():
    return render_template('settings.html')

@app.route('/run', methods=['POST'])
def run():
    data = request.json
    repo_url = data.get('repo_url')
    task_type = data.get('task_type', 'test')
    custom_command = data.get('custom_command', '')
    if not repo_url:
        return jsonify({"status": "error", "message": "No repo URL provided"}), 400
    run_id = datetime.now().strftime('%Y%m%d%H%M%S')
    runs = load_runs()
    new_run = {
        'id': run_id,
        'repo_url': repo_url,
        'task_type': task_type,
        'custom_command': custom_command,
        'status': 'running',
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'report': None
    }
    runs.append(new_run)
    save_runs(runs)
    thread = threading.Thread(target=execute_run, args=(run_id, repo_url, task_type, custom_command))
    thread.start()
    return jsonify({"status": "ok", "run_id": run_id})

@app.route('/runs', methods=['GET'])
def get_runs():
    runs = load_runs()
    return jsonify(runs)

@app.route('/run/<run_id>', methods=['GET'])
def get_run(run_id):
    runs = load_runs()
    run = next((r for r in runs if r['id'] == run_id), None)
    if not run:
        return jsonify({"error": "Run not found"}), 404
    return jsonify(run)

@app.route('/report/<run_id>')
def view_report(run_id):
    runs = load_runs()
    run = next((r for r in runs if r['id'] == run_id), None)
    if not run:
        return "Run not found", 404
    return render_template('report.html', run=run)

def execute_run(run_id, repo_url, task_type, custom_command):
    from executor import Executor
    executor = Executor()
    executor.run(run_id, repo_url, task_type, custom_command)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
