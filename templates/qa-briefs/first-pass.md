You are reviewing an interactive tunnel-book pop-up story.

Book: {{book}}
Audience: {{audience}}
Design rules: {{rules}}
Notes: {{notes}}

Judge only what is visible in the supplied screenshots. Say when evidence is unclear. Do not invent hidden text or behaviour.

The left page carries the story and controls. A slider pull tab moves the scene. A lesson flap sits on the picture and reveals a lesson. A fact booklet opens to show supporting facts. A paper wheel turns to reveal changing information.

The right page is a tunnel-book pop-up stage. It uses layered paper scenery, cut-outs, depth and a grounded floor. Controls should feel attached to the paper mechanisms they move.

Screenshot names describe pages and states. Start is the resting state. Half is the slider at its midpoint. Pulled is the completed slider state. Lifted is the open lesson flap. Final is the completed interactive state. Sheet images compare several states.

Check these visual criteria:

- Composition, hierarchy and balance
- Clear type, contrast and reading order
- Clipping, overlap and hidden controls
- Grounding, depth and believable paper construction
- Slider, flap, booklet and wheel affordances
- Consistency between interaction states
- Phone and print layout when those images are present
- Calm detail suitable for the audience

Give concrete fixes. Name the image and region. State what should move, resize, recolour or change. Prioritise visible defects over personal taste.

Return only one JSON object with these fields:

- `verdict`: One or two plain sentences.
- `scores`: An object with numeric scores from 0 to 10 for overall, composition, typography, interaction_affordance, consistency, phone and print.
- `defects`: An array. Each item has id, severity, image, where, problem and fix. Severity is blocker, major, minor or polish.
- `suggestions`: An array of concrete improvements. Each item has id, impact, effort, idea, why and how.
- `recheck`: An empty array for this first pass.
