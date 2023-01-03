use pyo3::prelude::*;

pub mod membership;
pub mod road_network;
pub mod geoid;
pub mod entity_position;
pub mod link;
pub mod utils;

use membership::Membership;
use road_network::RoadNetwork;
use geoid::Geoid;
use entity_position::EntityPosition;
use link::LinkTraversal;


/// A Python module implemented in Rust.
#[pymodule]
fn hive_core(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<Membership>()?;
    m.add_class::<RoadNetwork>()?;
    m.add_class::<Geoid>()?;
    m.add_class::<EntityPosition>()?;
    m.add_class::<LinkTraversal>()?;
    Ok(())
}