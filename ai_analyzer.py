import anthropic
import json
import re
import random
import os

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

def generate_run_id():
    return str(random.randint(10000, 99999))

def analyze_results(results):
    run_id = results.get('run_id', 'unknown')
    repo_url = results.get('repo_url', 'unknown')
    task_type = results.get('task_type', 'unknown')
    language = results.get('language', 'unknown')
    execution_time = results.get('execution_time', 0)
    steps = results.get('steps', {})

    clone = steps.get('clone', {})
    install = steps.get('install', {})
    task = steps.get('task', {})

    task_output = task.get('output', '')
    task_success = task.get('success', False)

    overall_status = detect_smart_status(task_output, task_success, clone, install)
    test_counts = extract_test_counts(task_output)
    ai_data = get_ai_analysis(repo_url, task_type, language, clone, install, task, execution_time, overall_status)

    report = {
        'run_id': generate_run_id(),
        'repo_url': repo_url,
        'task_type': task_type,
        'language': language,
        'overall_status': overall_status,
        'execution_time': execution_time,
        'tests_passed': test_counts['passed'],
        'tests_failed': test_counts['failed'],
        'steps': {
            'clone': {
                'status': 'success' if clone.get('success') else 'fail',
                'output': clone.get('output', '')[:500]
            },
            'install': {
                'status': 'success' if install.get('success') else 'fail',
                'output': install.get('output', '')[:500]
            },
            'task': {
                'status': 'success' if task.get('success') else 'fail',
                'output': task.get('output', '')[:2000],
                'command': task.get('command', ''),
                'return_code': task.get('return_code', -1)
            }
        },
        'root_cause': ai_data['root_cause'],
        'impact': ai_data['impact'],
        'likely_fix': ai_data['likely_fix'],
        'suggested_commands': ai_data['suggested_commands'],
        'confidence': ai_data['confidence'],
        'ai_analysis': ai_data['analysis']
    }

    return report

def extract_test_counts(task_output):
    passed = 0
    failed = 0
    m1 = re.search(r'(\d+) failed.*?(\d+) passed', task_output)
    m2 = re.search(r'(\d+) passed.*?(\d+) failed', task_output)
    m3 = re.search(r'(\d+) passing', task_output)
    m4 = re.search(r'(\d+) failing', task_output)
    m5 = re.search(r'Tests:\s+(\d+) failed,\s+(\d+) passed', task_output)
    m6 = re.search(r'Tests:\s+(\d+) passed', task_output)
    if m1: failed=int(m1.group(1)); passed=int(m1.group(2))
    elif m2: passed=int(m2.group(1)); failed=int(m2.group(2))
    elif m5: failed=int(m5.group(1)); passed=int(m5.group(2))
    elif m6: passed=int(m6.group(1))
    else:
        if m3: passed=int(m3.group(1))
        if m4: failed=int(m4.group(1))
    return {'passed': passed, 'failed': failed}

def detect_smart_status(task_output, task_success, clone, install):
    if not clone.get('success', False):
        return 'FAILED'
    passed = 0
    failed = 0
    m1 = re.search(r'(\d+) failed.*?(\d+) passed', task_output)
    m2 = re.search(r'(\d+) passed.*?(\d+) failed', task_output)
    m3 = re.search(r'(\d+) passing', task_output)
    m4 = re.search(r'(\d+) failing', task_output)
    m5 = re.search(r'Tests:\s+(\d+) failed,\s+(\d+) passed', task_output)
    if m1: failed=int(m1.group(1)); passed=int(m1.group(2))
    elif m2: passed=int(m2.group(1)); failed=int(m2.group(2))
    elif m5: failed=int(m5.group(1)); passed=int(m5.group(2))
    else:
        if m3: passed=int(m3.group(1))
        if m4: failed=int(m4.group(1))
    if passed > 0 or failed > 0:
        total = passed + failed
        pass_rate = passed / total if total > 0 else 0
        if pass_rate == 1.0: return 'PASSED'
        elif pass_rate >= 0.5: return 'PARTIALLY PASSED'
        else: return 'FAILED'
    if task_success: return 'PASSED'
    return 'FAILED'

def calculate_confidence(overall_status, clone, install, task, task_output):
    if not clone.get('success', False): return 20
    if not install.get('success', False): return 45
    if overall_status == 'PASSED': return 95
    if overall_status == 'PARTIALLY PASSED': return 82
    if task_output and len(task_output) > 100: return 78
    return 50

def get_ai_analysis(repo_url, task_type, language, clone, install, task, execution_time, overall_status):
    try:
        task_output = task.get('output', 'No output')[:2000]
        task_success = task.get('success', False)
        install_output = install.get('output', '')[:500]
        clone_success = clone.get('success', False)
        confidence = calculate_confidence(overall_status, clone, install, task, task_output)

        if overall_status == 'PASSED':
            prompt = f"""You are an expert software engineer analyzing a successful build/test execution.

Repository: {repo_url}
Task Type: {task_type}
Language: {language}
Overall Status: PASSED
Task Output:
{task_output}

Return a JSON object:
{{
  "root_cause": "All checks passed successfully",
  "impact": "No issues detected — codebase is stable and ready",
  "likely_fix": "No fixes needed",
  "suggested_commands": ["npm run lint", "npm run coverage"],
  "analysis": [
    "What ran: describe what tests or build steps executed",
    "Coverage: mention what areas were tested based on output",
    "Next step: suggest what developer should do next like deploy or add more tests",
    "Health: give an overall health assessment of the codebase"
  ]
}}

Rules:
- analysis should have 3-5 meaningful points
- Each string starts with a label like 'What ran:', 'Coverage:', 'Next step:', 'Health:'
- Be specific based on actual output
- Return ONLY valid JSON. No markdown. No extra text."""

        elif overall_status == 'PARTIALLY PASSED':
            prompt = f"""You are an expert software engineer analyzing a partially passing build/test execution.

Repository: {repo_url}
Task Type: {task_type}
Language: {language}
Overall Status: PARTIALLY PASSED
Install Output: {install_output}
Task Output:
{task_output}

Return a JSON object:
{{
  "root_cause": "One clear sentence about the main failing issue",
  "impact": "One sentence about what this affects",
  "likely_fix": "One actionable sentence to fix it",
  "suggested_commands": ["command1", "command2"],
  "analysis": [
    "What passed: describe what tests passed successfully",
    "What failed: describe specifically what failed and why",
    "Root issue: explain the underlying cause clearly",
    "How to fix: specific steps to resolve the failing tests",
    "Priority: which fix should be done first"
  ]
}}

Rules:
- analysis should have 4-5 meaningful points
- Each string starts with a label
- Be specific and technical
- Return ONLY valid JSON. No markdown. No extra text."""

        else:
            prompt = f"""You are an expert software engineer analyzing a failed build/test execution.

Repository: {repo_url}
Task Type: {task_type}
Language: {language}
Overall Status: FAILED
Clone Success: {clone_success}
Install Output: {install_output}
Task Success: {task_success}
Task Output:
{task_output}

Return a JSON object:
{{
  "root_cause": "One clear sentence describing the main issue",
  "impact": "One sentence about what this affects",
  "likely_fix": "One actionable sentence",
  "suggested_commands": ["command1", "command2", "command3"],
  "analysis": [
    "What happened: one clear sentence",
    "What broke: specific thing that failed",
    "Why it broke: underlying reason",
    "How to fix: step 1",
    "How to fix: step 2 if needed"
  ]
}}

Rules:
- analysis should have 4-5 meaningful points
- Each string starts with a label
- Be specific and technical but readable
- Return ONLY valid JSON. No markdown. No extra text."""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )

        text = response.content[0].text.strip()
        text = re.sub(r'```json|```', '', text).strip()
        data = json.loads(text)

        analysis = data.get('analysis', [])
        if isinstance(analysis, list):
            analysis_text = '\n'.join(analysis)
        else:
            analysis_text = str(analysis)

        return {
            'root_cause': data.get('root_cause', 'Could not determine root cause'),
            'impact': data.get('impact', '—'),
            'likely_fix': data.get('likely_fix', '—'),
            'suggested_commands': data.get('suggested_commands', [])[:4],
            'confidence': confidence,
            'analysis': analysis_text
        }
    except Exception as e:
        print(f"❌ AI analysis failed: {e}")
        return {
            'root_cause': 'Could not determine root cause',
            'impact': '—',
            'likely_fix': '—',
            'suggested_commands': [],
            'confidence': 0,
            'analysis': 'AI analysis unavailable.'
        }