use std::{any, str::FromStr};

use h3ron::H3Cell;
use pyo3::prelude::*;
use serde::{Deserialize, Serialize};

use anyhow::{anyhow, Result};

use crate::geoid::Geoid;

pub fn geoids_to_link_id(origin: Geoid, destination: Geoid) -> String {
    format!(
        "{}-{}",
        origin.h3_cell.to_string(),
        destination.h3_cell.to_string()
    )
}

pub fn link_id_to_geoids(link_id: String) -> Result<(Geoid, Geoid)> {
    let ids: Vec<&str> = link_id.split("-").collect();
    if ids.len() != 2 {
        return Err(anyhow!("LinkId not in expected format of [Geoid]-[Geoid]"));
    } else {
        let start_str = ids[0];
        let start_h3 = H3Cell::from_str(start_str)?;
        let start = Geoid { h3_cell: start_h3 };
        let end_str = ids[1];
        let end_h3 = H3Cell::from_str(end_str)?;
        let end = Geoid { h3_cell: end_h3 };
        return Ok((start, end));
    }
}

#[pyclass]
#[derive(Clone, Serialize, Deserialize)]
pub struct RoadNetwork {}
