use std::collections::HashSet;

use pyo3::{exceptions::PyValueError, prelude::*, types::PyType};

const PUBLIC_MEMBERSHIP_ID: &str = "public";

#[pyclass]
#[derive(Clone)]
pub struct Membership {
    #[pyo3(get)]
    memberships: HashSet<String>,
}

#[pymethods]
impl Membership {
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

    // fn memberships_in_common(&self, other_membership: Membership) -> HashSet<String> {
    //     let memberships: HashSet<_> = self.memberships.intersection(&other_membership.memberships).collect::<HashSet<String>>();
    //     memberships
    // }
}

