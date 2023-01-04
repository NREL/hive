use anyhow::Result;
use h3ron::H3DirectedEdge;

use crate::geoid::{Geoid, GeoidString};

/// Return the h3 line distance between two Geoid strings
pub fn h3_dist_km(origin_string: &GeoidString, destination_string: &GeoidString) -> Result<f64> {
    let origin = Geoid::from_string(origin_string.to_owned())?;
    let destination = Geoid::from_string(destination_string.to_owned())?;
    let edge = H3DirectedEdge::from_cells(origin.h3_cell, destination.h3_cell)?;
    let length_km = edge.length_km()?;
    Ok(length_km)
}
