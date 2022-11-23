use std::collections::HashSet;

use pyo3::{
    exceptions::PyValueError,
    prelude::*,
    types::{PyDict, PyType},
};

use serde::{Deserialize, Serialize};

const PUBLIC_MEMBERSHIP_ID: &str = "public";

#[pyclass]
#[derive(Clone, Serialize, Deserialize)]
pub struct Membership {
    #[pyo3(get)]
    memberships: HashSet<String>,
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
    fn new(memberships: Option<HashSet<String>>) -> PyResult<Self> {
        match memberships {
            Some(m) => {
                if m.iter().any(|m| m == &PUBLIC_MEMBERSHIP_ID) {
                    return Err(PyValueError::new_err(format!(
                        "{} is reserved, please use another membership id",
                        PUBLIC_MEMBERSHIP_ID
                    )));
                }
                Ok(Self { memberships: m })
            }
            None => Ok(Self {
                memberships: HashSet::new(),
            }),
        }
    }
    #[classmethod]
    fn from_tuple(_: &PyType, member_ids: Vec<String>) -> PyResult<Self> {
        Self::new(Some(HashSet::from_iter(member_ids)))
    }
    #[classmethod]
    fn single_membership(_: &PyType, membership_id: String) -> PyResult<Self> {
        Self::new(Some(HashSet::from([membership_id])))
    }

    #[getter]
    fn public(&self) -> bool {
        self.memberships.is_empty()
    }

    fn add_membership(&self, member_id: String) -> PyResult<Self> {
        if member_id == PUBLIC_MEMBERSHIP_ID {
            return Err(PyValueError::new_err(format!(
                "{} is reserved, please use another membership id",
                PUBLIC_MEMBERSHIP_ID
            )));
        }
        let mut new_memberships = self.memberships.clone();
        new_memberships.insert(member_id);
        Self::new(Some(new_memberships))
    }

    fn memberships_in_common(&self, other_membership: &Membership) -> HashSet<String> {
        let result: HashSet<_> = self
            .memberships
            .intersection(&other_membership.memberships)
            .map(|m| m.clone())
            .collect();
        result
    }

    fn has_memberships_in_common(&self, other_membership: &Membership) -> bool {
        !self
            .memberships
            .intersection(&other_membership.memberships)
            .collect::<HashSet<_>>()
            .is_empty()
    }

    fn grant_access_to_membership(&self, other_membership: &Membership) -> bool {
        self.public() || self.has_memberships_in_common(other_membership)
    }

    fn grant_access_to_membership_id(&self, member_id: String) -> bool {
        self.public() || self.memberships.contains(&member_id)
    }

    fn to_json(&self) -> Vec<String> {
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
            memberships: HashSet::from(["a".to_string(), "b".to_string()]),
        }
    }

    fn membership_b() -> Membership {
        Membership {
            memberships: HashSet::from(["b".to_string(), "c".to_string()]),
        }
    }

    fn membership_c() -> Membership {
        Membership {
            memberships: HashSet::from(["x".to_string(), "y".to_string()]),
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
