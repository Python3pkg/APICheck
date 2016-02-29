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


class TestFailedException(Exception):

    """Exception class raised when any test fails

    This exception is raised when any test reaches a failure point.

    """

    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


class APICheck:

    """Main class for loading and running tests.

    This class is used to load and run tests from a JSON file.
    Each instance tracks the statistics the set of tests most recently
    run in that instance.

    """

    def __init__(self, base_url, fname):
        """Initialize the APICheck object.

        Loads tests from the given filename and initializes all
        statistics to 0.

        :param fname: path to test file

        """

        self.base_url = base_url
        self.load_tests_file(fname)
        self.passed = 0
        self.failed = 0
        self.total_elapsed_time = 0

    def load_tests_file(self, fname):
        """Load tests from given file into tests instance variable

        :param fname: path to test file

        """

        with open(fname) as data_file:
            self.tests = json.load(data_file)

    def run_all_tests(self):
        """Runs all loaded tests."""

        # Keep track of stats
        self.results = []
        total_start_time = time.time()

        # Instance variables passed and failed contain stats
        # for the most recently run set of tests
        self.passed = 0
        self.failed = 0

        # Run and time each test
        for index, test in enumerate(self.tests):

            # Time the test until finished or until an exception occurs.
            test_start_time = time.time()

            try:

                self.__run_test(test)

                test_elapsed_time = time.time() - test_start_time

                self.results.append(
                    {
                        "name": test["name"],
                        "status": "PASSED",
                        "elapsed_time": test_elapsed_time
                    }
                )

                self.passed += 1

            except TestFailedException as e:

                # The test stops at first error it encounters.
                # User receives feedback about the first error only.
                test_elapsed_time = time.time() - test_start_time

                try:
                    test_name = test["name"]
                except KeyError:
                    test_name = "ERROR: NAME NOT PROVIDED"

                self.results.append(
                    {
                        "name": test_name,
                        "status": "FAILED",
                        "elapsed_time": test_elapsed_time,
                        "error_msg": str(e)
                    }
                )

                self.failed += 1

        # Instance variable total_elapsed_time contains the
        # total runtime of the most recently run set of tests
        self.total_elapsed_time = time.time() - total_start_time

    def write_results_to_file(self, format, fname):
        """Writes results to given filename.

        :param format: output format - must be either 'json' or 'text'
        :param fname: output filename

        """

        with open(fname, 'w') as outfile:
            self.__output_results(format, outfile)

    def print_results(self, format):
        """Prints results to stdout.

        :param format: output format - must be either 'json' or 'text'

        """

        self.__output_results(format)

    def __run_test(self, test):
        """Run an individual test.

        :param test: a map represnting a test. Must have keys 'name','url', and 'method'

        """

        try:

            # Assigning vars checks for keys, ensuring that the test
            # is correctly formed
            name = test["name"]
            url =  self.base_url + test["url"]
            method = test["method"]

            if method.upper() == "GET":
                r = requests.get(url)

            elif method.upper() == "POST":

                if "payload" in test:
                    r = requests.post(url, json=test["payload"])
                else:
                    r = requests.post(url)

            else:
                msg = "Malformed test. Allowed methods are GET and POST"
                raise TestFailedException(msg)

            resp = r.json()

        except KeyError as e:
            msg = "Malformed test. Must provide '%s' in tests file." \
                % str(e.args[0])
            raise TestFailedException(msg)

        except ValueError as e:
            raise TestFailedException("Could not decode JSON from response.")

        try:

            # Run all checks for expected exact JSON response values
            if "expected_response_values" in test:

                for key in test["expected_response_values"]:

                    exp_val = test["expected_response_values"][key]

                    if exp_val != resp[key]:

                        msg = "Expected value '%s' at key '%s' but got '%s'." \
                            % (str(exp_val), str(key), str(resp[key]))

                        raise TestFailedException(msg)

            # Run all checks for expected types in JSON response
            if "expected_response_types" in test:

                for key in test["expected_response_types"]:

                    exp_type = test["expected_response_types"][key]
                    val = resp[key]

                    if exp_type == "string":
                        self.__test_expected_type(key, val, str)
                    elif exp_type == "int":
                        self.__test_expected_type(key, val, int)
                    elif exp_type == "float":
                        self.__test_expected_type(key, val, float)
                    else:
                        raise TestFailedException(
                            "Malformed test. Expected types allowed: 'str', 'int', 'float'")

        except KeyError as e:
            raise TestFailedException("Expected key '%s' not found."
                                      % str(e.args[0]))

    def __test_expected_type(self, key, val, exp_type):
        """Check whether the type of val equals the expected type

        :param key: the key being checked
        :param val: the value whose type will be checked
        :param exp_type: the type expected for val

        """

        if not isinstance(val, exp_type):
            raise TestFailedException(
                self.__get_expected_type_error_message(key, val, exp_type))

    def __get_expected_type_error_message(self, key, val, expected_type):
        """Return a formatted error message for expected type errors.

        :param key: the key being checked
        :param val: the value causing the error
        :param expected_type: the type expected by the test

        """

        return "Invalid type at key '%s'. Expected '%s' got '%s'." \
               % (str(key), str(expected_type), str(type(val)))

    def __output_results(self, format="json", outstream=sys.stdout):
        """Output the results to the provided output stream.

        :param format: the desired output format - default 'json'
        :param outstream: the desired output stream - default stdout

        """

        try:

            total_tests = self.passed + self.failed
            total_tests = total_tests if total_tests > 0 else 1
            success_percent = (self.passed / total_tests) * 100

            if format.upper() == "JSON":

                res_json = {
                    "summary": {
                        "passed": self.passed,
                        "failed": self.failed,
                        "success_percentage": success_percent,
                        "total_elapsed_time": self.total_elapsed_time
                    },
                    "test_results": self.results
                }

                json.dump(res_json, outstream, indent=4)

            elif format.upper() == "TEXT":

                outstream.write("***\n")
                outstream.write("TEST SUMMARY\n")
                outstream.write("------------\n")
                outstream.write("Tests passed: %i\n" % self.passed)
                outstream.write("Tests failed: %i\n" % self.failed)

                outstream.write("Success percentage : %.2f%%\n"
                                % round(success_percent, 2))
                outstream.write("Total elapsed time: %.3f seconds\n"
                                % self.total_elapsed_time)
                outstream.write("***\n")

                for res in self.results:

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

        checker = APICheck(args.api_base_url,args.test_file_name)
        checker.run_all_tests()
        checker.print_results(args.format)

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

    
