from problem.models import Problem, ProblemRuleType
from submission.models import JudgeStatus, Submission
from problem.utils import parse_problem_template
import subprocess
import os
import time
import sys
import hashlib
import shutil
import re

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
        result, err_result = execute_once(problem, submission, test_case)
        result["test_case"] = index
        results.append(result)
    if(err_result["err"] == 1):
        final_results = err_result
    else:
        final_results["data"] = results
    print(final_results)
    return final_results


def execute_once(problem, submission, test_case):
    executer = {
        "Python3": execute_python,
        "Java": execute_java,
        "C++": execute_cpp,
        "C": execute_c99,
    }

    hash_name = create_hash_dict(submission.code)
    result,err_result = executer[submission.language](problem, submission, test_case, hash_name)
    temp_dir_path = os.path.join(os.path.abspath(os.sep), 'temp', hash_name)
    shutil.rmtree(temp_dir_path)
    return result,err_result


def execute_python(problem, submission, test_case, hash_name):
    temp_dir_path = os.path.join(os.path.abspath(os.sep), 'temp', hash_name)
    file_name = os.path.join(temp_dir_path, f"{hash_name}.py")
    #print(file_name)
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
        "test_case": None 
    }
    err_result = {
        "err": 0,
        "data": None
    }
    try:
        start_time = time.time()
        start_cpu_time = time.process_time()
        execute_result = subprocess.run(
            args=[sys.executable, file_name],
            input=test_case.input,
            text=True,
            capture_output=True,
            timeout=problem.time_limit,
        )
        #print(execute_result)
        end_cpu_time = time.process_time()
        end_time = time.time()
        output = execute_result.stdout.strip()
        result_dict["real_time"] = end_time - start_time
        result_dict["cpu_time"] = end_cpu_time - start_cpu_time
        result_dict["exit_code"] = execute_result.returncode
        result_dict["output_md5"] = hashlib.md5(output.encode()).hexdigest()  
        #print("real_output:{},output:{}".format(output, test_case.output))
        if execute_result.returncode != 0:
            if(execute_result.stderr == ""):
                result_dict["result"] = 4
            else:
                err_result["err"] = 1
                err_result["data"] = re.sub(r'(/[^/ ]*)+/?|(?i)\b[a-z]:[\\/][^\s]*', '', execute_result.stderr)
        elif output == test_case.output:
            result_dict["result"] = 0
        else:
            result_dict["result"] = -1
    except subprocess.TimeoutExpired as e:
        result_dict["result"] = 2

    os.remove(file_name)
    #print(err_result)
    return result_dict,err_result


def execute_java(problem, submission, test_case, hash_name):
    temp_dir_path = os.path.join(os.path.abspath(os.sep), 'temp', hash_name)
    class_name = "Main"
    code_file_name = os.path.join(temp_dir_path, f"{class_name}.java")
    class_file_name = os.path.join(temp_dir_path, f"{class_name}.class")
    with open(code_file_name, "w", encoding='utf-8') as f:
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
        "test_case": None 
    }
    err_result = {
        "err": 0,
        "data": None
    }
    try:
        compile_result = subprocess.run(
            args=["javac", "-d", temp_dir_path, code_file_name],
            text=True,
            capture_output=True,
            timeout=5,  # 5 seconds for compilation
        )
        if compile_result.returncode != 0:
            if compile_result.stderr == "":
                result_dict["result"] = 4  # Compilation Error
            else:
                err_result["err"] = 1
                err_result["data"] = re.sub(r'(/[^/ ]*)+/?|(?i)\b[a-z]:[\\/][^\s]*', '', compile_result.stderr)
            return result_dict, err_result

        start_time = time.time()
        start_cpu_time = time.process_time()
        execute_result = subprocess.run(
            args=["java", "-cp", temp_dir_path, class_name],
            input=test_case.input,
            text=True,
            capture_output=True,
            timeout=problem.time_limit,
        )
        end_cpu_time = time.process_time()
        end_time = time.time()
        output = execute_result.stdout.strip()
        result_dict["real_time"] = end_time - start_time
        result_dict["cpu_time"] = end_cpu_time - start_cpu_time
        result_dict["exit_code"] = execute_result.returncode
        result_dict["output_md5"] = hashlib.md5(output.encode()).hexdigest()
        if execute_result.returncode != 0:
            if execute_result.stderr == "":
                result_dict["result"] = 4  # Runtime Error
            else:
                err_result["err"] = 1
                err_result["data"] = re.sub(r'(/[^/ ]*)+/?|(?i)\b[a-z]:[\\/][^\s]*', '', execute_result.stderr)
        elif output == test_case.output:
            result_dict["result"] = 0  # Accepted
        else:
            result_dict["result"] = -1  # Wrong Answer
    except subprocess.TimeoutExpired as e:
        result_dict["result"] = 2  # Time Limit Exceeded

    os.remove(code_file_name)
    os.remove(class_file_name)
    return result_dict, err_result

def execute_c(problem, submission, test_case, hash_name, mode="cpp"):
    temp_dir_path = os.path.join(os.path.abspath(os.sep), 'temp', hash_name)
    code_file_name = os.path.join(temp_dir_path, f"{hash_name}.{mode}")
    exe_file_name = os.path.join(temp_dir_path, f"{hash_name}.exe")
    compiler = "g++" if mode == "cpp" else "gcc"
    
    os.makedirs(temp_dir_path, exist_ok=True)
    
    with open(code_file_name, "w", encoding='utf-8') as f:
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
        "test_case": None
    }
    
    err_result = {
        "err": 0,
        "data": None
    }
    
    try:
        compile_result = subprocess.run(
            args=[compiler, code_file_name, "-o", exe_file_name],
            text=True,
            capture_output=True,
            timeout=5,  # 5 seconds for compilation
        )
        if compile_result.returncode != 0:
            if compile_result.stderr == "":
                result_dict["result"] = 4  # Compilation Error
            else:
                err_result["err"] = 1
                err_result["data"] = re.sub(r'(/[^/ ]*)+/?|(?i)\b[a-z]:[\\/][^\s]*', '', compile_result.stderr)
            return result_dict, err_result

        start_time = time.time()
        start_cpu_time = time.process_time()
        execute_result = subprocess.run(
            args=[exe_file_name],
            input=test_case.input,
            text=True,
            capture_output=True,
            timeout=problem.time_limit,
        )
        end_cpu_time = time.process_time()
        end_time = time.time()
        
        output = execute_result.stdout.strip()
        result_dict["real_time"] = end_time - start_time
        result_dict["cpu_time"] = end_cpu_time - start_cpu_time
        result_dict["exit_code"] = execute_result.returncode
        result_dict["output_md5"] = hashlib.md5(output.encode()).hexdigest()
        
        if execute_result.returncode != 0:
            if execute_result.stderr == "":
                result_dict["result"] = 4  # Runtime Error
            else:
                err_result["err"] = 1
                err_result["data"] = re.sub(r'(/[^/ ]*)+/?|(?i)\b[a-z]:[\\/][^\s]*', '', execute_result.stderr)
        elif output == test_case.output:
            result_dict["result"] = 0  # Accepted
        else:
            result_dict["result"] = -1  # Wrong Answer
    except subprocess.TimeoutExpired as e:
        result_dict["result"] = 2  # Time Limit Exceeded

    os.remove(code_file_name)
    os.remove(exe_file_name)
    
    return result_dict, err_result




def execute_cpp(problem, submission, test_case, hash_name):
    return execute_c(problem, submission, test_case, hash_name, mode="cpp")


def execute_c99(problem, submission, test_case, hash_name):
    return execute_c(problem, submission, test_case, hash_name, mode="c")

