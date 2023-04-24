use anyhow::Result;
use h3ron::ToCoordinate;

use crate::geoid::Geoid;
use crate::type_aliases::*;

const EARTH_RADIUS: f64 = 6371.0;

pub fn haversine(lat1: f64, lon1: f64, lat2: f64, lon2: f64) -> f64 {
    let dlat = (lat2 - lat1).to_radians();
    let dlon = (lon2 - lon1).to_radians();

    let a = (dlat / 2.0).sin().powi(2)
        + (dlon / 2.0).sin().powi(2) * lat1.to_radians().cos() * lat2.to_radians().cos();

    let c = 2.0 * a.sqrt().asin();

    let distance = c * EARTH_RADIUS;

    distance
}

/// Return the line distance between two Geoid strings
pub fn h3_dist_km(origin_string: &GeoidString, destination_string: &GeoidString) -> Result<f64> {
    let origin = Geoid::from_string(origin_string.to_owned())?;
    let destination = Geoid::from_string(destination_string.to_owned())?;
    let origin_coord = origin.h3_cell.to_coordinate()?;
    let dest_coord = destination.h3_cell.to_coordinate()?;
    let distance_km = haversine(origin_coord.y, origin_coord.x, dest_coord.y, dest_coord.x);
    Ok(distance_km)
}
