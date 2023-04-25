/// Add IntoPy for a newtype struct which wraps a type that already implements IntoPy.
#[macro_export]
macro_rules! newtype_into_py {
    ($name:ident) => {
        impl $crate::pyo3::prelude::IntoPy<$crate::pyo3::prelude::PyObject> for $name {
            fn into_py(self, py: $crate::pyo3::prelude::Python) -> $crate::pyo3::prelude::PyObject {
                self.0.into_py(py)
            }
        }
    };
}
