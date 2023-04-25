/// Create a newtype struct with the given name and type.
/// Additionally implement IntoPy so that the struct can be passed to Python.
#[macro_export]
macro_rules! pystruct {
    ($name:ident, $type:ty) => {
        #[derive(
            $crate::derive_more::Deref,
            $crate::derive_more::Display,
            $crate::derive_more::From,
            $crate::derive_more::FromStr,
            $crate::derive_more::Into,
            $crate::serde::Deserialize,
            $crate::serde::Serialize,
            $crate::pyo3::prelude::FromPyObject,
            Clone,
            Eq,
            Hash,
            PartialEq,
        )]
        pub struct $name($type);
        impl $crate::pyo3::prelude::IntoPy<$crate::pyo3::prelude::PyObject> for $name {
            fn into_py(self, py: $crate::pyo3::prelude::Python) -> $crate::pyo3::prelude::PyObject {
                self.0.into_py(py)
            }
        }
    };
}
