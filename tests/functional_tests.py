
import unittest

# build outputs hierarchy - JH
class TestOutputStructure(unittest.TestCase):

    def setUp(self):
        pass

    def test_build_output_root(self):
        unittest.assertEqual(1,0)

    def tearDown(self):
        pass


# Pre-process input requests - BB
class TestPreProcess(unittest.TestCase):

    def setUp(self):
        pass
    
    def test_filter_short_trips(self):
        unittest.assertEqual(1,0)

    def test_filter_outlier_trips(self):
        unittest.assertEqual(1,0)
    
    # pool individual requests (static pooling)
    def test_pool_requests(self):
        unittest.assertEqual(1,0)

    # trip chains/sequencing for dynamic pooling

    def tearDown(self):
        pass



# Initialize - NR
class TestInitialization(unittest.TestCase):

    def setUp(self):
        pass

    # calculate domain variables (net scaling factor, average dispatch speed)
    def test_domain_variable_calcs(self):
        unittest.assertEqual(1,0)
    
    # charging objects
    def test_init_charging_objects(self):
        unittest.assertEqual(1,0)

    # vehicle objects - set SOC etc
    def test_init_vehicle_objects(self):
        unittest.assertEqual(1,0)

    def tearDown(self):
        pass
    

class TestDispatcherDefinition(unittest.TestCase):

    def setUp(self):
        pass

    # test_invalid_dispatch

    # test_valid_dispatch

    def tearDown(self):
        pass
    



# Run - time-marching - NR/BB
    # Collect requests from time-step (at least one)
    # pass request(s) to dispatcher(s)
    # dispatcher(s) assign vehicle actions
    # All objects updates (vehicles, chargers, fleet)
    # global sync if necessary
    # Capture state in log(s) update

# Outputs - NR/BB
    # writing outputs
    # checking output contents (expected files, features, sizes etc)


if __name__ == '__main__':
    unittest.main()