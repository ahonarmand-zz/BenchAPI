import unittest
import json
import unittest.mock as mock

from bench import BenchAPIDAO, Transaction, DailyRunningBalance
import requests

resp_json = {
            "totalCount": 5,
            "page": 4,
            "transactions": [{
                "Date": "2013-12-13",
                "Ledger": "Insurance Expense",
                "Amount": "-100.81",
                "Company": "Bench"
            }
            ]
        }

class BenchDAOTestCase(unittest.TestCase):
    def setUp(self):
        self.benchDAO = BenchAPIDAO("test.com/{page}.json")

    def _mock_response(self,status=200,content="CONTENT",
                        json_data=None, raise_for_status=None):
        '''
        Creates mock response objects.
        This method was adopted from: https://gist.github.com/evansde77/45467f5a7af84d2a2d34f3fcb357449c
        '''    
        mock_resp = mock.Mock()
        # mock raise_for_status call w/optional error
        mock_resp.raise_for_status = mock.Mock()
        if raise_for_status:
            mock_resp.raise_for_status.side_effect = raise_for_status
        # set status code and content
        mock_resp.status_code = status
        mock_resp.content = content
        # add json data if provided
        if json_data:
            mock_resp.json = mock.Mock(
                return_value=json_data
            )
        return mock_resp

    def test_convert_json_to_transaction_list_one_record(self):
        transactions = self.benchDAO.convert_json_to_transaction_list(resp_json["transactions"])
        self.assertEqual(transactions[0].amount, -100.81)
        self.assertEqual(transactions[0].company, "Bench")

    def test_convert_json_to_transaction_list_one_record_with_no_amount_field(self):
        transactions = self.benchDAO.convert_json_to_transaction_list([{"Date": "2013-12-13","Ledger": "Insurance Expense","Company": "Bench"}])
        self.assertEqual(len(transactions), 0)

    @mock.patch.object(requests, 'get')
    def test_retrieve_next_page_connection_error(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError()
        with self.assertRaises(SystemExit):
            self.benchDAO.retrieve_next_page(4)
    
    @mock.patch.object(requests, 'get')
    def test_retrieve_next_page_timeout_error(self, mock_get):
        mock_get.side_effect = requests.exceptions.Timeout()
        with self.assertRaises(SystemExit):
            self.benchDAO.retrieve_next_page(4)
        
    @mock.patch.object(requests, 'get')
    def test_retrieve_next_page_timeout_followed_by_reponse(self, mock_get):
        mock_get.side_effect = [requests.exceptions.Timeout(), self._mock_response(json_data=resp_json)]
        page = self.benchDAO.retrieve_next_page(4)
        self.assertEqual(page.transactions[0].amount, -100.81)

    @mock.patch.object(requests, 'get')
    def test_retrieve_next_page_response_with_one_record(self, mock_get):
        mock_resp = self._mock_response(json_data=resp_json)
        mock_get.return_value = mock_resp

        page = self.benchDAO.retrieve_next_page(4)
        self.assertEqual(page.transactions[0].amount, -100.81)
        self.assertEqual(page.transactions[0].date, "2013-12-13")
        self.assertEqual(page.transactions[0].company, "Bench")
        self.assertEqual(page.transactions[0].ledger, "Insurance Expense")

    @mock.patch.object(requests, 'get')
    def test_retrieve_next_page_response_with_two_records(self, mock_get):
        resp_json = {
            "totalCount": 5,
            "page": 4,
            "transactions": [{
                "Date": "2013-12-13",
                "Ledger": "Insurance Expense",
                "Amount": "-100.81",
                "Company": "Bench"
            },
            {
                "Date": "2018-01-01",
                "Ledger": "Beer",
                "Amount": "-1000",
                "Company": "Bench"
            }
            ]
        }
        mock_resp = self._mock_response(json_data=resp_json)
        mock_get.return_value = mock_resp

        page = self.benchDAO.retrieve_next_page(4)
        self.assertEqual(page.total_count, 5)
        self.assertEqual(page.transactions[0].amount, -100.81)
        self.assertEqual(page.transactions[1].amount, -1000)

    @mock.patch.object(requests, 'get')
    def test_pull_all_transactions_with_two_pages(self, mock_get):
        resp_json_1 = {
            "totalCount": 2,
            "page": 1,
            "transactions": [{
                "Date": "2013-12-13",
                "Ledger": "Insurance Expense",
                "Amount": "-100.81",
                "Company": "Bench"
            }
            ]
        }
        resp_json_2 = {
            "totalCount": 2,
            "page": 2,
            "transactions": [{
                "Date": "2013-12-13",
                "Ledger": "Insurance Expense",
                "Amount": "-5.43",
                "Company": "Bench"
            }
            ]
        }
        mock_resp_1 = self._mock_response(json_data=resp_json_1)
        mock_resp_2 = self._mock_response(json_data=resp_json_2)

        mock_get.side_effect = [mock_resp_1, mock_resp_2]

        self.benchDAO.pull_all_transactions()
        self.assertEqual(self.benchDAO.transactions[0].amount, -100.81)
        self.assertEqual(self.benchDAO.transactions[1].amount, -5.43)

    @mock.patch.object(requests, 'get')
    def test_pull_all_transactions_with_one_page(self, mock_get):
        resp_json_1 = {
            "totalCount": 1,
            "page": 1,
            "transactions": [{
                "Date": "2013-12-13",
                "Ledger": "Insurance Expense",
                "Amount": "-100.81",
                "Company": "Bench"
            }
            ]
        }
        mock_resp_1 = self._mock_response(json_data=resp_json_1)
        mock_get.side_effect = [mock_resp_1]

        self.benchDAO.pull_all_transactions()
        self.assertEqual(self.benchDAO.transactions[0].amount, -100.81)

    @mock.patch.object(requests, 'get')
    def test_pull_all_transactions_with_one_page_but_no_records(self, mock_get):
        resp_json_1 = {
            "totalCount": 0,
            "page": 1,
            "transactions": []
        }
        mock_resp_1 = self._mock_response(json_data=resp_json_1)
        mock_get.return_value = mock_resp_1

        self.benchDAO.pull_all_transactions()
        self.assertEqual(len(self.benchDAO.transactions), 0)

    def test_calculate_total_balance_with_three_records(self):
        self.benchDAO.transactions = [Transaction("2018-01-01", "CIBC", 1.5, "Bench"),
                                    Transaction("2018-01-01", "CIBC", -4.5, "Bench"),
                                    Transaction("2018-01-01", "CIBC", 5, "Bench")]
        self.assertEqual(self.benchDAO.calculate_total_balance(), 2)

    def test_calculate_total_balance_no_records(self):
        self.benchDAO.transactions = []
        self.assertEqual(self.benchDAO.calculate_total_balance(), 0)

    def test_calculate_running_daily_balance_one_record(self):
            self.benchDAO.transactions = [Transaction("2018-01-01", "CIBC", 1.5, "Bench")]
            result = self.benchDAO.calculate_running_daily_balance()
            self.assertEqual(result[0].date, "2018-01-01")
            self.assertEqual(result[0].running_balance, 1.5)

    def test_calculate_running_daily_balance_two_records_with_same_date(self):
            self.benchDAO.transactions = [Transaction("2018-01-01", "CIBC", 1.5, "Bench"),
                                        Transaction("2018-01-01", "CIBC", 5, "Bench")]
            result = self.benchDAO.calculate_running_daily_balance()
            self.assertEqual(result[0].date, "2018-01-01")
            self.assertEqual(result[0].running_balance, 6.5)

    def test_calculate_running_daily_balance_four_records_with_no_order(self):
        self.benchDAO.transactions = [Transaction("2018-01-02", "CIBC", -4.5, "Bench"),
                                    Transaction("2018-01-02", "CIBC", 5, "Bench"),
                                    Transaction("2018-01-01", "CIBC", 1.5, "Bench"),
                                    Transaction("2018-01-03", "CIBC", 10, "Bench")]
        result = self.benchDAO.calculate_running_daily_balance()
        self.assertEqual(result[0].date, "2018-01-01")
        self.assertEqual(result[0].running_balance, 1.5)
        self.assertEqual(result[1].date, "2018-01-02")
        self.assertEqual(result[1].running_balance, 2)
        self.assertEqual(result[2].date, "2018-01-03")
        self.assertEqual(result[2].running_balance, 12)
    

if __name__ == '__main__':
    unittest.main()