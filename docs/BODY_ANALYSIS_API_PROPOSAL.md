# Body Analysis API Proposal (Phase 2)

This proposal extends the current manual-input styling MVP without breaking existing flows.

## Product Phases

- Phase 1 (current): user fills form -> recommendation + optional image previews.
- Phase 2 (new): user uploads full-body photos -> backend body analysis -> structured profile -> recommender uses profile.

## API Design

### 1) Upload Full-Body Photos

- **Method**: `POST /api/v1/body-analysis/upload`
- **Content-Type**: `multipart/form-data`
- **Fields**:
  - `user_id` (string)
  - `photos` (1-2 files)
- **Response**:

```json
{
  "user_id": "demo-user",
  "photos": [
    {
      "photo_id": "uuid",
      "filename": "full_body_1.jpg",
      "content_type": "image/jpeg"
    }
  ]
}
```

### 2) Analyze Body Profile

- **Method**: `POST /api/v1/body-analysis/analyze`
- **Content-Type**: `application/json`
- **Request**:

```json
{
  "user_id": "demo-user",
  "photo_ids": ["uuid-1", "uuid-2"]
}
```

- **Response**:

```json
{
  "user_id": "demo-user",
  "photo_ids": ["uuid-1", "uuid-2"],
  "profile": {
    "estimated_height_range": "168-174 cm",
    "estimated_weight_range": "68-78 kg",
    "shoulder_type": "balanced",
    "waist_type": "natural_waist",
    "thigh_type": "balanced",
    "leg_ratio": "balanced",
    "overall_build": "balanced",
    "body_subtype": "balanced_everyday",
    "styling_direction": "clean casual, straight fit pants, light outerwear, avoid skinny pants"
  }
}
```

## Structured Body Profile Fields

- `estimated_height_range` (photo-based estimate, not exact)
- `estimated_weight_range` (photo-based estimate, not exact)
- `shoulder_type`
- `waist_type`
- `thigh_type`
- `leg_ratio`
- `overall_build`
- `body_subtype`
- `styling_direction`

## Integration Plan

1. Keep existing `RecommendRequest.body_profile` as-is.
2. Map analyzed profile to recommendation tags before composition.
3. Add confidence score and analysis metadata in later iterations.
4. Replace mock service with a real vision model adapter when ready.

## Notes

- Current implementation is mock-only (no CV/ML inference).
- API boundaries are designed for easy future model replacement.
