import os
from unittest import TestLoader, TextTestRunner

from pengine_utils import PEngineUtils

loader = TestLoader()
suite = loader.discover(
    os.path.join(PEngineUtils.subprojectPyPath("testing"), "testspace")
)

runner = TextTestRunner(verbosity=0)
runner.run(suite)
