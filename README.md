# APICheck

A web API testing tool for JSON based APIs. Written in Python.

The tool runs a set of tests defined in a simple JSON configuration file and
checks the HTTP response against expected JSON values or types. 

## Installation

The easiest way to install is by using pip:

```
sudo pip install apicheck
```

Otherwise from the command line:

```
git clone https://github.com/kuykendb/APICheck
cd apicheck
sudo python setup.py install
```

NOTE: the current beta release has only been tested with Python v3. Testing will
soon be done for v2 as well.

## Usage

The tool must be provided a JSON file of tests to be run. A basic example of a
file of tests is:

```
[
	{
		"name":"My First Test",
		"url":"/posts/1",
		"method":"GET",
		"expected_response_values":{
			"id":1
		},
		"expected_response_types":{
			"body":"string"
		}
	}
]
```

You can run the above example test by saving the above JSON in a file called
"tests.json" and then by running the following command:

```
apicheck http://jsonplaceholder.typicode.com tests.json
```

This runs a test against an API that provides fake JSON responses for testing 
purposes. You should see the following after running this test:

```
{
    "test_results": [
        {
            "status": "PASSED",
            "elapsed_time": 1.021967887878418,
            "name": "My First Test"
        }
    ],
    "summary": {
        "total_elapsed_time": 1.0219738483428955,
        "passed": 1,
        "success_percentage": 100.0,
        "failed": 0
    }
}
```

If you don't need the output in JSON and want to see a more human readable 
output, then just pass the flag `-f` or `--format` with the argument `text`:

For example:
```
apicheck http://jsonplaceholder.typicode.com tests.json -f text
```

### Test File Format

The JSON file of tests must contain an array of test objects. Each test object
must contain the following required keys:

```
name: a string describing the test
endpoint: the endpoint to be tested which will be appended to the base url
method: the HTTP request method - either GET or POST 
```

Each test can run any number of checks on the JSON response object 
returned by the request. Each check can test that a key in the response is
mapped to the correct value or the correct type.

#### Checking Response Values

Checks for expected values are described in the `expected_response_values` map
for each test.

For example if we expect the JSON response to have an `id` key with a value of `2`
and a `title` key with a value of `qui est esse` then our `expected_response_values`
map would look like the following:

```
"expected_response_values":{
	"id":2,
	"title": "qui est esse"
}
```

#### Checking Response Types

Checks for expected tyles are described in the `expected_response_types` map for
each test.

For example if we expect the JSON response to have an `id` key with an `int` value
and a `title` key with a `string` value, then our `expected_response_types` 

```
"expected_response_types":{
	"id":"int",
	"title": "string"
}
```

The expected types that can be checked are:
```
string
int
float
```

#### Full Example Test File

The following is a full example of a simple test file:

```
[
	{
		"name":"My First Test",
		"url":"/posts/1",
		"method":"GET",
		"expected_response_values":{
			"id":1
		}
	},
	{
		"name":"My Second Test",
		"url":"/posts/2",
		"method":"GET",
		"expected_response_values":{
			"id":2,
			"title":"qui est esse"
		},
		"expected_response_types":{
			"userId":"int",
			"body":"string"
		}
	},
	{
		"name":"My Third Test",
		"url":"/posts/3",
		"method":"GET",
		"expected_response_types":{
			"userId":"int",
			"title":"string",
			"body":"string"
		}
	}
]
```

To run the above example, save the JSON in a file called `tests.json` and then
run the following command:

```
apicheck http://jsonplaceholder.typicode.com tests.json
```


