use std::collections::HashSet;

use pyo3::{
    exceptions::PyValueError,
    prelude::*,
    types::{PyDict, PyType},
};
use serde::{Deserialize, Serialize};

use crate::type_aliases::*;

const PUBLIC_MEMBERSHIP_ID: &str = "public";

#[pyclass]
#[derive(Clone, Serialize, Deserialize)]
pub struct Membership {
    #[pyo3(get)]
    memberships: HashSet<MembershipId>,
}

impl Default for Membership {
    fn default() -> Self {
        Membership {
            memberships: HashSet::new(),
        }
    }
}

// TODO: eventually we'll move all the pymethods into here
impl Membership {
    pub fn _new(memberships: Option<HashSet<MembershipId>>) -> Result<Self, String> {
        match memberships {
            Some(m) => {
                if m.iter()
                    .any(|m| m == &PUBLIC_MEMBERSHIP_ID.to_string().into())
                {
                    return Err(format!(
                        "{} is reserved, please use another membership id",
                        PUBLIC_MEMBERSHIP_ID
                    ));
                }
                Ok(Self { memberships: m })
            }
            None => Ok(Self {
                memberships: HashSet::new(),
            }),
        }
    }
    pub fn _from_tuple(member_ids: Vec<MembershipId>) -> Result<Self, String> {
        Membership::_new(Some(HashSet::from_iter(member_ids)))
    }
}

#[pymethods]
impl Membership {
    pub fn copy(&self) -> Self {
        self.clone()
    }
    pub fn __copy__(&self) -> Self {
        self.clone()
    }
    pub fn __deepcopy__(&self, _memo: &PyDict) -> Self {
        self.clone()
    }

    #[new]
    fn new(memberships: Option<HashSet<MembershipId>>) -> PyResult<Self> {
        Membership::_new(memberships).map_err(PyValueError::new_err)
    }
    #[classmethod]
    pub fn from_tuple(_: &PyType, member_ids: Vec<MembershipId>) -> PyResult<Self> {
        Self::new(Some(HashSet::from_iter(member_ids)))
    }

    #[classmethod]
    pub fn single_membership(_: &PyType, membership_id: MembershipId) -> PyResult<Self> {
        Self::new(Some(HashSet::from([membership_id])))
    }

    #[getter]
    pub fn public(&self) -> bool {
        self.memberships.is_empty()
    }

    pub fn add_membership(&self, member_id: MembershipId) -> PyResult<Self> {
        if member_id == PUBLIC_MEMBERSHIP_ID.to_string().into() {
            return Err(PyValueError::new_err(format!(
                "{} is reserved, please use another membership id",
                PUBLIC_MEMBERSHIP_ID
            )));
        }
        let mut new_memberships = self.memberships.clone();
        new_memberships.insert(member_id);
        Self::new(Some(new_memberships))
    }

    pub fn memberships_in_common(&self, other_membership: &Membership) -> HashSet<MembershipId> {
        let result: HashSet<_> = self
            .memberships
            .intersection(&other_membership.memberships)
            .map(|m| m.clone())
            .collect();
        result
    }

    pub fn has_memberships_in_common(&self, other_membership: &Membership) -> bool {
        !self
            .memberships
            .intersection(&other_membership.memberships)
            .collect::<HashSet<_>>()
            .is_empty()
    }

    pub fn grant_access_to_membership(&self, other_membership: &Membership) -> bool {
        self.public() || self.has_memberships_in_common(other_membership)
    }

    pub fn grant_access_to_membership_id(&self, member_id: MembershipId) -> bool {
        self.public() || self.memberships.contains(&member_id)
    }

    pub fn to_json(&self) -> Vec<MembershipId> {
        self.memberships.iter().map(|mid| mid.clone()).collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn public_membership() -> Membership {
        Membership {
            memberships: HashSet::new(),
        }
    }

    fn membership_a() -> Membership {
        Membership {
            memberships: HashSet::from(["a".to_string().into(), "b".to_string().into()]),
        }
    }

    fn membership_b() -> Membership {
        Membership {
            memberships: HashSet::from(["b".to_string().into(), "c".to_string().into()]),
        }
    }

    fn membership_c() -> Membership {
        Membership {
            memberships: HashSet::from(["x".to_string().into(), "y".to_string().into()]),
        }
    }

    #[test]
    fn test_membership() {
        let public = public_membership();
        let ma = membership_a();
        let mb = membership_b();
        let mc = membership_c();

        assert!(public.grant_access_to_membership(&ma));
        assert!(public.grant_access_to_membership(&public));
        assert!(public.grant_access_to_membership(&mb));
        assert!(public.grant_access_to_membership(&mc));

        assert!(ma.grant_access_to_membership(&mb));
        assert!(mb.grant_access_to_membership(&ma));

        assert!(!ma.grant_access_to_membership(&public));
        assert!(!ma.grant_access_to_membership(&mc));
        assert!(!mc.grant_access_to_membership(&ma));
    }
}
