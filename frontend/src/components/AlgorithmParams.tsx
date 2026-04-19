import type {
  AlgorithmParamsMap,
  DpRSEParams,
  LievensParams,
  MLParams,
} from "../types";

export const DEFAULT_LIEVENS: LievensParams = {
  coefficient_a: 1.0,
  coefficient_b: 0.0,
  coefficient_c: 0.0,
  use_fcf_weighting: true,
  temporal_window_days: 12,
};

export const DEFAULT_DPRSE: DpRSEParams = {
  use_land_cover_mask: true,
  mask_forest: true,
};

export const DEFAULT_ML: MLParams = {
  model_id: "xgboost_regional_v1",
};

interface Props {
  algorithmId: string;
  params: AlgorithmParamsMap;
  onChange: (next: AlgorithmParamsMap) => void;
}

const fieldsetStyle: React.CSSProperties = {
  border: "1px solid #e5e7eb",
  borderRadius: 4,
  padding: 10,
  marginTop: 8,
};

const legendStyle: React.CSSProperties = {
  fontSize: 12,
  fontWeight: 600,
  color: "#374151",
};

const numberInputStyle: React.CSSProperties = {
  width: "100%",
  marginTop: 2,
};

export function AlgorithmParams({ algorithmId, params, onChange }: Props) {
  if (algorithmId === "lievens") {
    const current = params.lievens ?? DEFAULT_LIEVENS;
    const update = (patch: Partial<LievensParams>) =>
      onChange({ ...params, lievens: { ...current, ...patch } });
    return (
      <fieldset style={fieldsetStyle}>
        <legend style={legendStyle}>Lievens parameters</legend>
        <label style={{ fontSize: 12 }}>
          Coefficient A
          <input
            type="number"
            step="0.01"
            value={current.coefficient_a}
            onChange={(e) => update({ coefficient_a: Number(e.target.value) })}
            style={numberInputStyle}
          />
        </label>
        <label style={{ fontSize: 12 }}>
          Coefficient B
          <input
            type="number"
            step="0.01"
            value={current.coefficient_b}
            onChange={(e) => update({ coefficient_b: Number(e.target.value) })}
            style={numberInputStyle}
          />
        </label>
        <label style={{ fontSize: 12 }}>
          Coefficient C
          <input
            type="number"
            step="0.01"
            value={current.coefficient_c}
            onChange={(e) => update({ coefficient_c: Number(e.target.value) })}
            style={numberInputStyle}
          />
        </label>
        <label style={{ fontSize: 12 }}>
          Temporal window (days)
          <input
            type="number"
            min={1}
            step="1"
            value={current.temporal_window_days}
            onChange={(e) => update({ temporal_window_days: Number(e.target.value) })}
            style={numberInputStyle}
          />
        </label>
        <label style={{ fontSize: 12, display: "flex", alignItems: "center", gap: 6, marginTop: 6 }}>
          <input
            type="checkbox"
            checked={current.use_fcf_weighting}
            onChange={(e) => update({ use_fcf_weighting: e.target.checked })}
          />
          Forest-cover-fraction weighting
        </label>
      </fieldset>
    );
  }

  if (algorithmId === "dprse") {
    const current = params.dprse ?? DEFAULT_DPRSE;
    const update = (patch: Partial<DpRSEParams>) =>
      onChange({ ...params, dprse: { ...current, ...patch } });
    return (
      <fieldset style={fieldsetStyle}>
        <legend style={legendStyle}>DpRSE parameters</legend>
        <label style={{ fontSize: 12, display: "flex", alignItems: "center", gap: 6 }}>
          <input
            type="checkbox"
            checked={current.use_land_cover_mask}
            onChange={(e) => update({ use_land_cover_mask: e.target.checked })}
          />
          Apply land-cover mask
        </label>
        <label style={{ fontSize: 12, display: "flex", alignItems: "center", gap: 6, marginTop: 4 }}>
          <input
            type="checkbox"
            checked={current.mask_forest}
            onChange={(e) => update({ mask_forest: e.target.checked })}
          />
          Mask forested pixels
        </label>
      </fieldset>
    );
  }

  if (algorithmId === "ml") {
    const current = params.ml ?? DEFAULT_ML;
    const update = (patch: Partial<MLParams>) =>
      onChange({ ...params, ml: { ...current, ...patch } });
    return (
      <fieldset style={fieldsetStyle}>
        <legend style={legendStyle}>ML parameters (experimental)</legend>
        <label style={{ fontSize: 12 }}>
          Model ID
          <input
            type="text"
            value={current.model_id}
            onChange={(e) => update({ model_id: e.target.value })}
            style={numberInputStyle}
          />
        </label>
        <div style={{ fontSize: 11, color: "#9ca3af", marginTop: 4 }}>
          Production model not yet trained — see Phase 5.
        </div>
      </fieldset>
    );
  }

  return null;
}
