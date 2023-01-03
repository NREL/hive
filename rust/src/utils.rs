use anyhow::Result;
use h3ron::H3DirectedEdge;

use crate::geoid::Geoid;

/// Return the h3 line distance between two Geoids
pub fn h3_dist_km(origin: Geoid, destination: Geoid) -> Result<f64> {
    let edge = H3DirectedEdge::from_cells(origin.h3_cell, destination.h3_cell)?;
    let length_km = edge.length_km()?;
    Ok(length_km)
}

