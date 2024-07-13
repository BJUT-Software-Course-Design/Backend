from problem.models import Problem, ProblemRuleType
from submission.models import JudgeStatus, Submission
from problem.utils import parse_problem_template
import subprocess
import os
import time
import sys
import hashlib
import psutil
import shutil


def create_hash_dict(code):
    hash_name = hashlib.md5(code.encode() + str(time.time()).encode()).hexdigest()
    temp_dir_path = os.path.join(os.path.abspath(os.sep), 'temp', hash_name)
    os.makedirs(temp_dir_path, exist_ok=True)
    return hash_name


def execute_all(problem, submission, test_cases):
    final_results = {
        "err": 0,
        "data": None
    }
    results = []
    for index, test_case in enumerate(test_cases, start=1):
        result = execute_once(problem, submission, test_case)
        result["test_case"] = index
        results.append(result)
    final_results["data"] = results
    #print(final_results)
    return final_results


def execute_once(problem, submission, test_case):
    executer = {
        "Python3": execute_python,
        "Java": execute_java,
        "C++": execute_cpp,
        "C": execute_c99,
    }

    hash_name = create_hash_dict(submission.code)
    result = []
    result = executer[submission.language](problem, submission, test_case, hash_name, result)
    temp_dir_path = os.path.join(os.path.abspath(os.sep), 'temp', hash_name)
    shutil.rmtree(temp_dir_path)
    return result


def execute_python(problem, submission, test_case, hash_name,result):
    temp_dir_path = os.path.join(os.path.abspath(os.sep), 'temp', hash_name)
    file_name = os.path.join(temp_dir_path, f"{hash_name}.py")
    print(file_name)
    #print(submission.code)
    with open(file_name, "w", encoding='utf-8') as f:
        f.write(submission.code)
    result_dict = {
        "cpu_time": None,
        "result": None,
        "memory": None,
        "real_time": None,
        "signal": 0,
        "error": 0,
        "exit_code": None,
        "output_md5": None,
        "test_case": None  # 假设test_case有一个id属性
    }
    err_result = {
        "err": 0,
        "data": None
    }
    try:
        start_time = time.time()
        execute_result = subprocess.run(
            args=[sys.executable, file_name],
            input=test_case.input,
            text=True,
            capture_output=True,
            timeout=problem.time_limit,
        )
        print(execute_result)
        end_time = time.time()
        output = execute_result.stdout.strip()
        result_dict["real_time"] = end_time - start_time
        result_dict["exit_code"] = execute_result.returncode
        result_dict["output_md5"] = hashlib.md5(output.encode()).hexdigest()  
        print("real_output:{},output:{}".format(output, test_case.output))
        if execute_result.returncode != 0:
            result_dict["result"] = 4
        elif output == test_case.output:
            result_dict["result"] = 0
        else:
            result_dict["result"] = -1
    except subprocess.TimeoutExpired as e:
        result_dict["result"] = 2

    os.remove(file_name)

    return result_dict


def execute_java(problem, submission, test_case, hash_name, result):
    class_name = "Main"
    code_file_name = f"temp/{hash_name}/{class_name}.java"
    class_file_name = f"temp/{hash_name}/{class_name}.class"
    with open(code_file_name, "w") as f:
        f.write(submission.code)
    try:
        compile_result = subprocess.run(
            args=["javac", "-d", f"temp/{hash_name}", code_file_name],
            text=True,
            capture_output=False,
            timeout=5,  # 5 seconds for compilation
        )
        if compile_result.returncode != 0:
            result.result = "Compilation Error"
            return result
        start_time = time.time()
        execute_result = subprocess.run(
            args=["java", "-cp", f"temp/{hash_name}", class_name],
            input=test_case.input,
            text=True,
            capture_output=True,
            timeout=problem.time_limit
        )
        end_time = time.time()
        result.output = execute_result.stdout.strip()
        result.execution_time = end_time - start_time
        if execute_result.returncode != 0:
            result.result = "Runtime Error"
        elif result.output == test_case.output:
            result.result = "Accepted"
        else:
            result.result = "Wrong Answer"
    except subprocess.TimeoutExpired as e:
        result.result = "Time Limit Exceeded"
    result.memory_used = 0
    os.remove(code_file_name)
    os.remove(class_file_name)
    return result


def execute_c(problem, submission, test_case, hash_name, result, mode="cpp"):
    code_file_name = f"temp/{hash_name}/{hash_name}." + mode
    exe_file_name = f"temp/{hash_name}/{hash_name}.exe"
    compiler = "g++" if mode == "cpp" else "gcc"
    with open(code_file_name, "w") as f:
        f.write(submission.code)
    try:
        compile_result = subprocess.run(
            args=[compiler, code_file_name, "-o", exe_file_name],
            text=True,
            capture_output=False,
            timeout=5,  # 5 seconds for compilation
        )
        if compile_result.returncode != 0:
            result.result = "Compilation Error"
            return result
        start_time = time.time()
        execute_result = subprocess.run(
            args=[exe_file_name],
            input=test_case.input,
            text=True,
            capture_output=True,
            timeout=problem.time_limit,
        )
        end_time = time.time()
        result.output = execute_result.stdout.strip()
        result.execution_time = end_time - start_time
        if execute_result.returncode != 0:
            result.result = "Runtime Error"
        elif result.output == test_case.output:
            result.result = "Accepted"
        else:
            result.result = "Wrong Answer"
    except subprocess.CalledProcessError as e:
        result.result = "Runtime Error"
    except subprocess.TimeoutExpired as e:
        result.result = "Time Limit Exceeded"
    result.memory_used = 0
    os.remove(code_file_name)
    os.remove(exe_file_name)
    return result


def execute_cpp(problem, submission, test_case, hash_name, result):
    return execute_c(problem, submission, test_case, hash_name, result, mode="cpp")


def execute_c99(problem, submission, test_case, hash_name, result):
    return execute_c(problem, submission, test_case, hash_name, result, mode="c")

