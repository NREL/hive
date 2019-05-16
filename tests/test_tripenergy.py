import unittest

class TripEnergyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
    # this will run once before any of the test methods in this class

    # i.e. load or create sample dataset for the test class
        pass


    @classmethod
    def tearDownClass(cls):
    # this will run once after all of the test methods in this class

    # i.e. remove any files or databases that were created for testing
        pass

    def setUp(self):
    # This will run before EVERY test method in the class
        pass

    def tearDown(self):
    # This will run after EVERY test method in the class
        pass

    def test_import_whmi_template(self):
        pass

    def test_create_scaled_whmi(self):
        pass

    def test_calc_trip_kwh(self):
        pass

    def test_calc_idle_kwh(self):
        pass


if __name__ == '__main__':
    unittest.main()  