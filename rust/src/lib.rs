use pyo3::prelude::*;

mod macros;
mod type_aliases;

pub mod base;
pub mod entity_position;
pub mod geoid;
pub mod link;
pub mod membership;
pub mod resource;
pub mod road_network;
pub mod station;
pub mod utils;

// extern needed for imports to be available in macros
pub extern crate pyo3;

use base::Base;
use entity_position::EntityPosition;
use geoid::Geoid;
use link::LinkTraversal;
use membership::Membership;
use resource::Resource;
use road_network::HaversineRoadNetwork;

/// A Python module implemented in Rust.
#[pymodule]
fn hive_core(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<Membership>()?;
    m.add_class::<HaversineRoadNetwork>()?;
    m.add_class::<Geoid>()?;
    m.add_class::<EntityPosition>()?;
    m.add_class::<LinkTraversal>()?;
    m.add_class::<Base>()?;
    m.add_class::<Resource>()?;
    Ok(())
}
