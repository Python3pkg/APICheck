#!/usr/bin/python
# -*- coding: utf-8 -*-

# The MIT License (MIT)
#
# Copyright (c) 2016 Brad Kuykendall
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""APICheck is a web API testing tool for JSON based APIs.

The tool runs a set of tests defined in a JSON configuration file and
checks the HTTP response against expected JSON values or types.

For more information, see the project's Github page:

Basic test file contents:

    [
        {
            "name":"Get Test",
            "url":"http://jsonplaceholder.typicode.com/posts/1",
            "method":"GET",
            "expected_response_values":{
                "expected_key":"expected_value",
                "id":1,
                "title":"My Expected Title"
            },
            "expected_response_types":{
                "expected_key":"expected_type",
                "title":"string",
                "body":"string"
            }
        },
        {
            "name":"Test number 2",
            "url":"http://jsonplaceholder.typicode.com/posts/2",
            "method":"POST",
            ...

        },
        ...
    ]

    Notes:
    - name, url and method are required
    - expected_response_values and expected_response_types dictionaries are
        both optional, although one must be defined for any testing occur
    - expected types can be 'string', 'int' or 'float'

Usage:

    usage: apicheck test_file_name [-h] [-f FORMAT] 

    positional arguments:
        test_file_name        name of file containing JSON array of tests

    optional arguments:
        -h, --help                    show this help message and exit
        -f FORMAT, --format FORMAT    output format - must be either json or text

"""

import sys
import os
import argparse
import json
import time
import datetime

import requests


class Test:

    def __init__(self, name, endpoint, method, payload=None):
        """Initialize an API test.

        :param name: the name/description of a test
        :param endpoint: the endpoint for the request to be appended to base_url
        :param method: the HTTP request method - either GET or POST
        :param payload: a map containing the request payload

        """

        self.name = name
        self.endpoint = endpoint
        self.method = method
        self.expected_values = {}
        self.expected_types = {}
        self.payload = payload

    def add_expected_value(self, key, val):
        """Add expected value check to expected_values array

        :param key: the expected key
        :param type: the expected value

        """

        self.expected_values[key] = val

    def add_expected_type(self, key, type):
        """Add expected type check to expected_types array

        :param key: the expected key
        :param type: the expected type - string, int or float

        """

        self.expected_types[key] = type

    def run(self,base_url):
        """Run an individual test.

        :param base_url: the base url to be prepended to self.endpoint

        """

        url =  base_url + self.endpoint

        if self.method.upper() == "GET":
            r = requests.get(url)

        elif self.method.upper() == "POST":

            if self.payload is not None:
                r = requests.post(url, json=self.payload)
            else:
                r = requests.post(url)

        else:
            msg = "Malformed test. Allowed methods are GET and POST"
            return get_failure_object(msg)

        try:

            resp = r.json()

        except ValueError as e:

            msg = "Could not decode JSON from response."
            return get_failure_object(msg)

        try:

            # Run all checks for expected exact JSON response values
            for check_key in self.expected_values:

                exp_val = self.expected_values[check_key]

                if exp_val != resp[check_key]:

                    msg = "Expected value '%s' at key '%s' but got '%s'." \
                        % (str(exp_val), str(check_key), str(resp[check_key]))

                    return get_failure_object(msg)

            # Run all checks for expected types in JSON response
            for check_key in self.expected_types:

                exp_type = self.expected_types[check_key]
                val = resp[check_key]

                if exp_type == "string":
                    type_res = test_expected_type(val, str)

                elif exp_type == "int":
                    type_res = test_expected_type(val, int)

                elif exp_type == "float":
                    type_res = test_expected_type(val, float)

                else:
                    msg = "Malformed test. Expected types allowed: 'str',\
                          'int', 'float'"
                    return {"status": "FAILED", "error_msg": msg}

                if type_res == False:
                    msg = get_expected_type_error_message(check_key, val, exp_type)
                    return get_failure_object(msg)

            return {"status":"PASSED"}

        except KeyError as e:
            msg = "Expected key '%s' not found." % str(e.args[0])
            return get_failure_object(msg)

def get_failure_object(msg):
    """Get object returned for test failure.

    :param msg: the error message

    """

    return {"status": "FAILED", "error_msg": msg}


def run_tests_from_file(base_url, test_file_path, format):
    """Load the tests from a file in Test objects and run test.

    :param base_url: the base url of the API to be used for each test
    :param test_file_name: path the file of tests defined in JSON
    :param format: desired format for output - either json or text

    """
    

    with open(test_file_path) as data_file:
        
        tests_json = json.load(data_file)
        tests = []

        for t in tests_json:

            if "payload" in t:
                new_test = Test(t["name"], t["endpoint"], t["method"], t["payload"])
            else:
                new_test = Test(t["name"],t["endpoint"],t["method"])

            if "expected_response_values" in t:

                exp_vals = t["expected_response_values"]
                for key in exp_vals:

                    new_test.add_expected_value(key, exp_vals[key])

            if "expected_response_types" in t:

                exp_types = t["expected_response_types"]
                for key in exp_types:

                    new_test.add_expected_type(key, exp_types[key])

            tests.append(new_test)

        run_tests(base_url, tests, format)

def run_tests(base_url, tests, format):
    """Run all tests in provided tests array.

    :param base_url: the base url of the API to be used for each test
    :param tests: an array of Test objects
    :param format: the format to use for output - either json or text

    """


    # Keep track of stats
    results = []
    total_start_time = time.time()

    # Instance variables passed and failed contain stats
    # for the most recently run set of tests
    passed = 0
    failed = 0

    # Run and time each test
    for index, test in enumerate(tests):

        # Time the test until finished or until an exception occurs.
        test_start_time = time.time()

        result = test.run(base_url)

        test_elapsed_time = time.time() - test_start_time

        result["name"] = test.name
        result["elapsed_time"] = test_elapsed_time

        if result["status"] == "PASSED":
            passed += 1
        else:
            failed += 1

        results.append(result)

    # Instance variable total_elapsed_time contains the
    # total runtime of the most recently run set of tests
    total_elapsed_time = time.time() - total_start_time

    total_tests = passed + failed
    total_tests = total_tests if total_tests > 0 else 1
    success_percent = (passed / total_tests) * 100

    summary = {
        "passed": passed,
        "failed": failed,
        "success_percentage": success_percent,
        "total_elapsed_time": total_elapsed_time
    }

    output_results(results, summary, format)


def test_expected_type(val, exp_type):
    """Check whether the type of val equals the expected type

    :param val: the value whose type will be checked
    :param exp_type: the type expected for val

    """

    if not isinstance(val, exp_type):
        return False

def get_expected_type_error_message(key, val, expected_type):
    """Return a formatted error message for expected type errors.

    :param key: the key being checked
    :param val: the value causing the error
    :param expected_type: the type expected by the test

    """

    return "Invalid type at key '%s'. Expected '%s' got '%s'." \
           % (str(key), str(expected_type), str(type(val)))

def output_results(results, summary, format="json", outstream=sys.stdout):
    """Output the results to the provided output stream.

    :param results: the results to be printed
    :param summary: a summary of the results to be printed
    :param format: the desired output format - default 'json'
    :param outstream: the desired output stream - default stdout

    """

    try:

        if format.upper() == "JSON":

            res_json = {
                "summary": summary,
                "test_results": results
            }

            json.dump(res_json, outstream, indent=4)

        elif format.upper() == "TEXT":

            outstream.write("***\n")
            outstream.write("TEST SUMMARY\n")
            outstream.write("------------\n")
            outstream.write("Tests passed: %i\n" % summary["passed"])
            outstream.write("Tests failed: %i\n" % summary["failed"])

            outstream.write("Success percentage : %.2f%%\n"
                            % summary["success_percentage"])
            outstream.write("Total elapsed time: %.3f seconds\n"
                            % summary["total_elapsed_time"])
            outstream.write("***\n")

            for res in results:

                outstream.write("%s\n" % res["name"])
                outstream.write("\tStatus:%s\n" % res["status"])
                outstream.write("\tElapsed time: %f\n" % res["elapsed_time"])

                if(res["status"] == "FAILED"):
                    outstream.write("\tError message: %s\n"
                                    % res["error_msg"])

    except KeyError as e:
        print(str(e))

def main():
    """Main entry point for command line utility."""

    parser = argparse.ArgumentParser()

    parser.add_argument("api_base_url", type=str,
                        help="base url for all tests")
    parser.add_argument("test_file_name", type=str,
                        help="name of file containing JSON array of tests")
    parser.add_argument("-f", "--format", default="json", type=str,
                        help="output format - must be either json or text")

    args = parser.parse_args()

    try:

        run_tests_from_file(args.api_base_url, args.test_file_name, 
                                args.format)

    except KeyError as e:
        print("Required key '%s' not found. Check tests file." % str(e.args[0]))
        exit(1)

    except FileNotFoundError:
        print("Cannot open file '%s'. File not found." % args.test_file_name)
        exit(1)

    except ValueError:
        print("Cannot decode JSON from file '%s'." % args.test_file_name)
        exit(1)


if __name__ == "__main__":
    # This will only be executed when this module is run directly.
    # It provides the command line functionality of the module.
    main()
    
