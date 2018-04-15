# Bench Transaction API Retriever

### Installation

```
pip install -r requirements.txt
```

### Running the Tests
To run all tests:
```
python bench_test.py
```
To run a specific test:
```
python bench_test.py BenchDAOTestCase.<test_name>
```

### TODO: 
* add loggers to accommodate easier debugging and more fine-tuned tracking of the app. 
* Currently the application is keeping all the records received from the API in memory. If we are concerned about
memory usage, we can sort each page that we get from the server based on date and then save it to a file.
Since all files are sorted, we can tweak calculate_running_daily_balance() to construct the daily sums by iteratively reading the next
transaction from the file with the earliest date without loading the entire file into memory. This will be similar to the 
merge sort algorithm. 
* Concurrency: If there is a way to calculate how many pages we need to read from the start, then we can make the API calls
concurrently to increase the speed of the program. Currently, we don't know if there is a guarentee on the number of records 
per page, so the total number of pages cannot be calculated from the start. 
* If we are guarenteed that the records are already in order the sort in calculate_running_daily_balance() will be unnecessary.