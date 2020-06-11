# Copyright 2016 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Test DestroyPool.
"""

# isort: LOCAL
from stratisd_client_dbus import (
    Manager,
    MOBlockDev,
    ObjectManager,
    Pool,
    StratisdErrors,
    blockdevs,
    get_object,
    pools,
)
from stratisd_client_dbus._constants import TOP_OBJECT

from .._misc import SimTestCase, device_name_list

_DEVICE_STRATEGY = device_name_list(1)


class Destroy1TestCase(SimTestCase):
    """
    Test 'destroy' on empty database.

    'destroy' should always succeed on an empty database.
    """

    _POOLNAME = "deadpool"

    def setUp(self):
        """
        Start the stratisd daemon with the simulator.
        """
        super().setUp()
        self._proxy = get_object(TOP_OBJECT)

    def test_execution(self):
        """
        Destroy should succeed since there is nothing to pass to DestroyPool.
        """
        managed_objects = ObjectManager.Methods.GetManagedObjects(self._proxy, {})
        pool = next(pools(props={"Name": self._POOLNAME}).search(managed_objects), None)
        self.assertIsNone(pool)

    def test_bogus_object_path(self):
        """
        Success should occur on a bogus object path.
        """
        (_, return_code, _) = Manager.Methods.DestroyPool(self._proxy, {"pool": "/"})
        self.assertEqual(return_code, StratisdErrors.OK)


class Destroy2TestCase(SimTestCase):
    """
    Test 'destroy' on database which contains the given pool and an unknown
    number of devices.
    """

    _POOLNAME = "deadpool"

    def setUp(self):
        """
        Start the stratisd daemon with the simulator.
        """
        super().setUp()
        self._proxy = get_object(TOP_OBJECT)
        self._devices = _DEVICE_STRATEGY()
        Manager.Methods.CreatePool(
            self._proxy,
            {"name": self._POOLNAME, "redundancy": (True, 0), "devices": self._devices},
        )

    def test_execution(self):
        """
        The pool was just created, so it must always be possible to destroy it.
        """
        managed_objects = ObjectManager.Methods.GetManagedObjects(self._proxy, {})
        (pool1, _) = next(pools(props={"Name": self._POOLNAME}).search(managed_objects))
        blockdevs1 = blockdevs(props={"Pool": pool1}).search(managed_objects)
        self.assertEqual(
            frozenset(MOBlockDev(b).Devnode() for (_, b) in blockdevs1),
            frozenset(d for d in self._devices),
        )

        (result, return_code, _) = Manager.Methods.DestroyPool(
            self._proxy, {"pool": pool1}
        )

        managed_objects = ObjectManager.Methods.GetManagedObjects(self._proxy, {})
        blockdevs2 = blockdevs(props={"Pool": pool1}).search(managed_objects)
        pool2 = next(
            pools(props={"Name": self._POOLNAME}).search(managed_objects), None
        )

        self.assertEqual(return_code, StratisdErrors.OK)
        self.assertIsNone(pool2)
        self.assertTrue(result)
        self.assertEqual(len(list(blockdevs2)), 0)


class Destroy3TestCase(SimTestCase):
    """
    Test 'destroy' on database which contains the given pool and a volume.
    """

    _POOLNAME = "deadpool"
    _FSNAME = "vol"

    def setUp(self):
        """
        Start the stratisd daemon with the simulator.
        Create a pool and a filesystem.
        """
        super().setUp()
        self._proxy = get_object(TOP_OBJECT)
        ((_, (poolpath, _)), _, _) = Manager.Methods.CreatePool(
            self._proxy,
            {
                "name": self._POOLNAME,
                "redundancy": (True, 0),
                "devices": _DEVICE_STRATEGY(),
            },
        )
        Pool.Methods.CreateFilesystems(get_object(poolpath), {"specs": [self._FSNAME]})

    def test_execution(self):
        """
        This should fail since the pool has a filesystem on it.
        """
        managed_objects = ObjectManager.Methods.GetManagedObjects(self._proxy, {})
        (pool, _) = next(pools(props={"Name": self._POOLNAME}).search(managed_objects))

        ((is_some, _), return_code, _) = Manager.Methods.DestroyPool(
            self._proxy, {"pool": pool}
        )
        self.assertEqual(return_code, StratisdErrors.BUSY)
        self.assertFalse(is_some)

        managed_objects = ObjectManager.Methods.GetManagedObjects(self._proxy, {})
        (pool1, _) = next(pools(props={"Name": self._POOLNAME}).search(managed_objects))
        self.assertEqual(pool, pool1)