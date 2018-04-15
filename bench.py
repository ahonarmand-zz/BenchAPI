import requests
import sys, traceback

class MismatchingTotalCountError(Exception):
    '''
    This error is thrown when one of the subsequent pages
    retrieved does not have the same totalCount as the 
    first page.
    '''
    pass


class MismatchingPageNumber(Exception):
    '''Thrown when the page number in request and response do not match'''
    pass


class Page:
    '''stores the total_count and transactions reveived from a page'''
    def __init__(self, page_num ,total_count, transactions):
        self.page_num = page_num
        self.total_count = total_count
        self.transactions = transactions


class Transaction:
    '''The transactions read from API are deserialized into objects of this class'''
    def __init__(self, date, ledger, amount, company):
        self.date = date
        self.ledger = ledger
        self.amount = amount
        self.company = company


class DailyRunningBalance:
    '''a pair data structure storing the date and its daily running balance'''
    def __init__(self, date, running_balance):
        self.date = date
        self.running_balance = running_balance


class BenchAPIDAO:
    '''
    This class is an interface for the Bench API.
    It retrieves transactions from the API, stores them
    in the transactions attribute and calculates running 
    daily sum as well as total sum.
    '''
    def __init__(self, base_url="http://resttest.bench.co/transactions/{page}.json"):
        self.base_url = base_url
        self.transactions = []

    @staticmethod
    def convert_json_to_transaction_list(transactions):
        '''
        input: a list of json objects
        output: a list of Transaction objects
        '''
        result = []
        for trans in transactions:
            try:
                newTrans = Transaction(trans["Date"], trans["Ledger"], float(trans["Amount"]), trans["Company"])
            except ValueError:
                #ignore the record if it does not have a numeral Amount field
                continue
            except KeyError:
                #ignoring the record if it does not have Date, Ledger, Amount, or Company. 
                # We could potentially keep the ones that are missing only Company or Ledger
                continue
            result.append(newTrans)
        return result

    def retrieve_next_page(self, page_num):
        '''
        input: page_number
        output: a list of Transaction objects of all transactions on the page
        retrieves the page with page number equal to page_num.
        It will crash the program if the response cannot be decoded into json or if the json does not have totalCount
        or transactions fields. The exceptions are not handled so the user can be notified. Consider catching the 
        exception if there is a way to handle them gracefully.
        '''
        MAX_NUM_REQUEST_TRIES = 2
        TIME_OUT_SECONDS = 5
        num_tries = 0
        url = self.base_url.format(page=page_num)
        while num_tries < MAX_NUM_REQUEST_TRIES:
            try:
                response = requests.get(url, timeout = TIME_OUT_SECONDS)
                response.raise_for_status()         #throws an exception if we get HTTP codes other than 2xx
                resp_json = response.json()
                transactions = BenchAPIDAO.convert_json_to_transaction_list(resp_json["transactions"])
                if resp_json["page"] != page_num:
                    raise MismatchingPageNumber("Asked for page %d, but server responded with page %d" % (page_num, resp_json["page"]))
                return Page(page_num, resp_json["totalCount"], transactions)
            except requests.exceptions.Timeout as e:
                print("GET request to %s timed out. Retrying" % url)
                num_tries += 1
                if num_tries >= MAX_NUM_REQUEST_TRIES:
                    print("Server did not respond in time. Maximum number of retries reached. Exiting...")
                    traceback.print_exc(file=sys.stdout)
                    sys.exit(1)
            except requests.exceptions.ConnectionError as e:
                print("Could not connect to server. Connection error occured while accessing %s. Retrying..." % url)
                num_tries += 1
                if num_tries >= MAX_NUM_REQUEST_TRIES:
                    print("Maximum number of retries reached. Exiting...")
                    traceback.print_exc(file=sys.stdout)
                    sys.exit(1)
            except requests.exceptions.HTTPError as e:
                print("The server reponded with code: %d. Exiting..." % response.status_code)
                traceback.print_exc(file=sys.stdout)
                sys.exit(1)
            except KeyError as e:
                #This happens when the response does not have transactions, totalCount, or page fields.
                print("The response received from server is missing a field. Exiting...")
                traceback.print_exc(file=sys.stdout)
                sys.exit(1)
        
    def pull_all_transactions(self):
        '''pulls all transactions from the API and stores them in self.transactions'''
        num_records_read = 0
        total_count = None
        current_page = 1
        while (total_count == None) or (num_records_read < total_count):
            page = self.retrieve_next_page(current_page)
            self.transactions.extend(page.transactions)
            if total_count == None:
                total_count = page.total_count
            elif total_count != page.total_count:
                raise MismatchingTotalCountError("The total count on page %d does not match the total count on first page" % current_page)
            print("read page %d with %d records" % (page.page_num, len(page.transactions)))
            num_records_read += len(page.transactions)
            current_page += 1
        print("done reading all records")

    def calculate_total_balance(self):
        return sum(t.amount for t in self.transactions)
    
    def calculate_running_daily_balance(self):
        '''
        goes through self.transactions and for each date 
        calculates the balance up until that date.
        output: list of DailyRunningBalance objects
        '''
        self.transactions.sort(key =lambda t: t.date)
        running_daily = []
        prev_date = None
        if len(self.transactions) == 0:
            return running_daily
        else:
            prev_date = self.transactions[0].date
        running_sum = 0
        for i, trans in enumerate(self.transactions):
            if trans.date != prev_date:
                running_daily.append(DailyRunningBalance(prev_date, running_sum))
                prev_date = trans.date
            running_sum += trans.amount
            if i == len(self.transactions)-1:
                running_daily.append(DailyRunningBalance(trans.date, running_sum))
        return running_daily

    @staticmethod
    def print_running_daily_balance(running_daily_balance):
        for record in running_daily_balance:
            print("date: %s\trunning balance: %.2f" % (record.date, record.running_balance))


if __name__ == "__main__":
    benchDAO = BenchAPIDAO()
    benchDAO.pull_all_transactions()

    total_balance = benchDAO.calculate_total_balance()
    print("\n** total balance: %.2f\n" % total_balance)

    running_daily_balance = benchDAO.calculate_running_daily_balance()
    BenchAPIDAO.print_running_daily_balance(running_daily_balance)