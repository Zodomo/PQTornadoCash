#[path = "../../../../cryptanalysis/transcript/rust/transcript.rs"]
pub mod transcript;

use transcript::{Transcript, Variant};

pub fn create(parameter: &[u8; 64], public_values: &[u32]) -> Result<Transcript, &'static str> {
    Transcript::new(Variant::T3, parameter, public_values, false)
}
