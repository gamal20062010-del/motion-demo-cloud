# Checkout-based simulation

The archive audit's effective-tree simulation starts from a copy of the checked-in project directory, then copies base-archive files over it, then production-overlay files over that result. This models the actual checkout-first extraction behavior of the production workflow; files absent from an archive are not treated as deleted.

The comparison is made before the later workflow steps rewrite narration metadata, generate image variants and sound effects, and adjust the scene-four element position. Those later transformations are separate pipeline operations and are not evidence that an archive contains the source file.
