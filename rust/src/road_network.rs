use std::str::FromStr;

use h3ron::H3Cell;
use pyo3::{exceptions::PyValueError, prelude::*};
use serde::{Deserialize, Serialize};

use anyhow::{anyhow, Result};

use crate::{
    entity_position::EntityPosition, geoid::Geoid, link::LinkTraversal, utils::h3_dist_km,
};

const AVG_SPEED_KMPH: f64 = 40.0;

pub fn geoids_to_link_id(origin: Geoid, destination: Geoid) -> String {
    format!(
        "{}-{}",
        origin.h3_cell.to_string(),
        destination.h3_cell.to_string()
    )
}

pub fn link_id_to_geoids(link_id: &String) -> Result<(Geoid, Geoid)> {
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
pub struct RoadNetwork {
    sim_h3_resolution: usize,
}

#[pymethods]
impl RoadNetwork {
    #[new]
    fn new(sim_h3_resolution: usize) -> PyResult<Self> {
        Ok(RoadNetwork { sim_h3_resolution })
    }

    fn route(
        &self,
        origin: EntityPosition,
        destination: EntityPosition,
    ) -> PyResult<Vec<LinkTraversal>> {
        if origin == destination {
            return Ok(Vec::new());
        }

        let link_id = geoids_to_link_id(origin.geoid, destination.geoid);
        let link_dist_km = match h3_dist_km(origin.geoid, destination.geoid) {
            Err(e) => {
                return Err(PyValueError::new_err(format!(
                    "Failure computing h3 distance: {}",
                    e
                )))
            }
            Ok(dist) => dist,
        };

        let link = LinkTraversal {
            link_id: link_id,
            start: origin.geoid,
            end: destination.geoid,
            distance_km: link_dist_km,
            speed_kmph: AVG_SPEED_KMPH,
        };

        let route = vec![link];

        Ok(route)
    }

    fn distance_by_geoid_km(&self, origin: Geoid, destination: Geoid) -> PyResult<f64> {
        h3_dist_km(origin, destination)
            .map_err(|e| PyValueError::new_err(format!("Failure computing h3 distance: {}", e)))
    }

    fn link_from_link_id(&self, link_id: String) -> PyResult<LinkTraversal> {
        let (source, dest) = match link_id_to_geoids(&link_id) {
            Ok((source, dest)) => (source, dest),
            Err(e) => {
                return Err(PyValueError::new_err(format!(
                    "Error converting link id to geoid {}",
                    e
                )))
            }
        };
        let dist_km = self.distance_by_geoid_km(source, dest)?;
        let link = LinkTraversal {
            link_id: link_id,
            start: source,
            end: dest,
            distance_km: dist_km,
            speed_kmph: AVG_SPEED_KMPH,
        };
        Ok(link)
    }

    fn link_from_geoid(&self, geoid: Geoid) -> LinkTraversal {
        let link_id = geoids_to_link_id(geoid, geoid);
        let link = LinkTraversal {
            link_id: link_id,
            start: geoid,
            end: geoid,
            distance_km: 0.0,
            speed_kmph: 0.0,
        };
        link
    }
}
