import unittest, sys, os, xmlrunner
sys.path.append('pyfire')
from pyfire_test import TestPyFire

if __name__ == '__main__':
    testSuite = unittest.TestLoader().loadTestsFromTestCase(TestPyFire)
    xmlrunner.XMLTestRunner(output='reports').run(testSuite)
    
