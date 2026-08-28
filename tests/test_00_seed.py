"""
One-time SDK cache seed. Run ONCE, online: pytest tests/test_00_seed.py
Downloads and caches the pinned genvm SDK so glsim runs offline afterwards.
"""


SDK = "v0.2.16"
DUMMY_OWNER = "0x0000000000000000000000000000000000000001"




def test_seed_sdk_cache(direct_deploy):
    direct_deploy("contracts/steward_verifier.py", DUMMY_OWNER, sdk_version=SDK)
