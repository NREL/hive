use pyo3::{exceptions::PyValueError, prelude::*};
use serde::{Deserialize, Serialize};

use anyhow::{anyhow, Result};

pub type LinkId = String;

use crate::{
    entity_position::EntityPosition, geoid::GeoidString, link::LinkTraversal, utils::h3_dist_km,
};

const AVG_SPEED_KMPH: f64 = 40.0;

pub fn geoid_string_to_link_id(origin: &GeoidString, destination: &GeoidString) -> LinkId {
    format!("{}-{}", origin, destination)
}

pub fn link_id_to_geoids(link_id: &LinkId) -> Result<(GeoidString, GeoidString)> {
    let ids: Vec<&str> = link_id.split("-").collect();
    if ids.len() != 2 {
        return Err(anyhow!("LinkId not in expected format of [Geoid]-[Geoid]"));
    } else {
        let start_str = ids[0];
        let end_str = ids[1];
        return Ok((start_str.to_string(), end_str.to_string()));
    }
}

#[pyclass]
#[derive(Clone, Serialize, Deserialize)]
pub struct HaversineRoadNetwork {
    #[pyo3(get)]
    sim_h3_resolution: usize,
}

#[pymethods]
impl HaversineRoadNetwork {
    #[new]
    fn new(sim_h3_resolution: Option<usize>) -> PyResult<Self> {
        let res = match sim_h3_resolution {
            Some(res) => res,
            None => 15,
        };
        Ok(HaversineRoadNetwork {
            sim_h3_resolution: res,
        })
    }

    fn route(
        &self,
        origin: EntityPosition,
        destination: EntityPosition,
    ) -> PyResult<Vec<LinkTraversal>> {
        if origin == destination {
            return Ok(Vec::new());
        }

        let link_id = geoid_string_to_link_id(&origin.geoid, &destination.geoid);
        let link_dist_km = h3_dist_km(&origin.geoid, &origin.geoid)?;

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

    fn distance_by_geoid_km(&self, origin: GeoidString, destination: GeoidString) -> PyResult<f64> {
        h3_dist_km(&origin, &destination)
            .map_err(|e| PyValueError::new_err(format!("Failure computing h3 distance: {}", e)))
    }

    fn link_from_link_id(&self, link_id: LinkId) -> PyResult<LinkTraversal> {
        let (source, dest) = link_id_to_geoids(&link_id)?; 
        let dist_km = self.distance_by_geoid_km(source.clone(), dest.clone())?;
        let link = LinkTraversal {
            link_id: link_id,
            start: source,
            end: dest,
            distance_km: dist_km,
            speed_kmph: AVG_SPEED_KMPH,
        };
        Ok(link)
    }

    fn link_from_geoid(&self, geoid: GeoidString) -> LinkTraversal {
        let link_id = geoid_string_to_link_id(&geoid, &geoid);
        let link = LinkTraversal {
            link_id: link_id,
            start: geoid.clone(),
            end: geoid.clone(),
            distance_km: 0.0,
            speed_kmph: 0.0,
        };
        link
    }

    fn position_from_geoid(&self, geoid: GeoidString) -> EntityPosition {
        let link = self.link_from_geoid(geoid.clone());
        EntityPosition {
            link_id: link.link_id,
            geoid: geoid,
        }
    }

    fn geoid_within_geofence(&self, _geoid: GeoidString) -> bool {
        true
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn mock_network() -> HaversineRoadNetwork {
        HaversineRoadNetwork { sim_h3_resolution: 15 }
    }

    #[test]
    fn test_link_id_to_geoids()  {
        let link_id = "geoid1-geoid2".to_string();
        let (geoid1, geoid2) = link_id_to_geoids(&link_id).unwrap();
        assert_eq!(geoid1.as_str(), "geoid1");
        assert_eq!(geoid2.as_str(), "geoid2");
    }

    #[test]
    fn test_position_from_geoid()  {
        let network = mock_network();
        let geoid = "8f26dc934cccc69".to_string();
        let position = network.position_from_geoid(geoid);
        assert_eq!(position.geoid.as_str(), "8f26dc934cccc69");
        assert_eq!(position.link_id.as_str(), "8f26dc934cccc69-8f26dc934cccc69");

    }

}
