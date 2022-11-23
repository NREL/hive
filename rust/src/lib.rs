use pyo3::prelude::*;

pub mod membership;

use membership::Membership;


/// A Python module implemented in Rust.
#[pymodule]
fn hive_core(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<Membership>()?;
    Ok(())
}