/**
 * SkillList - Displays available OpenClaw skills and allows triggering them.
 * Fetches the skill list from the backend and renders as a scrollable list.
 */
import { useState, useEffect, VFC } from "react";
import {
  PanelSection,
  PanelSectionRow,
  ButtonItem,
} from "@decky/ui";
import { call } from "@decky/api";
import { colors, componentStyles, fontSize, spacing } from "../styles/theme";

/** Skill data structure from OpenClaw API */
interface Skill {
  name: string;
  description?: string;
  enabled?: boolean;
}

interface SkillListProps {
  /** Callback when user triggers a skill as a chat message */
  onTriggerSkill: (skillName: string) => void;
  onBack: () => void;
}

export const SkillList: VFC<SkillListProps> = ({ onTriggerSkill, onBack }) => {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchSkills();
  }, []);

  /** Fetch available skills from backend */
  const fetchSkills = async () => {
    setLoading(true);
    setError("");
    try {
      const result = await call<[], { success: boolean; skills: Skill[]; error?: string }>(
        "get_skills"
      );
      if (result.success) {
        setSkills(result.skills);
      } else {
        setError(result.error || "Failed to load skills");
      }
    } catch (e: any) {
      setError(e?.message || "Failed to fetch skills");
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <PanelSection title="Skills">
        {loading && (
          <PanelSectionRow>
            <div style={{ color: colors.textMuted, fontSize: `${fontSize.sm + 1}px`, textAlign: "center", width: "100%" }}>
              Loading skills...
            </div>
          </PanelSectionRow>
        )}

        {error && (
          <PanelSectionRow>
            <div style={{ color: colors.statusOffline, fontSize: `${fontSize.sm + 1}px`, textAlign: "center", width: "100%" }}>
              {error}
            </div>
          </PanelSectionRow>
        )}

        {!loading && !error && skills.length === 0 && (
          <PanelSectionRow>
            <div style={componentStyles.emptyState}>
              No skills available
            </div>
          </PanelSectionRow>
        )}

        {!loading && (
          <PanelSectionRow>
            <div
              style={{
                maxHeight: "360px",
                overflowY: "auto",
                width: "100%",
              }}
            >
              {skills.map((skill, i) => (
                <div
                  key={i}
                  style={componentStyles.skillCard}
                  onClick={() => onTriggerSkill(skill.name)}
                >
                  <div
                    style={{
                      fontSize: `${fontSize.md}px`,
                      fontWeight: "bold",
                      color: colors.textPrimary,
                      marginBottom: "2px",
                    }}
                  >
                    {skill.name}
                    {skill.enabled === false && (
                      <span style={{ color: colors.textMuted, fontSize: `${fontSize.sm}px`, marginLeft: "6px" }}>
                        (disabled)
                      </span>
                    )}
                  </div>
                  {skill.description && (
                    <div style={{ fontSize: `${fontSize.sm}px`, color: colors.textSecondary, lineHeight: "1.3" }}>
                      {skill.description}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </PanelSectionRow>
        )}

        {!loading && (
          <PanelSectionRow>
            <ButtonItem layout="below" onClick={fetchSkills}>
              Refresh
            </ButtonItem>
          </PanelSectionRow>
        )}
      </PanelSection>

      <PanelSection>
        <PanelSectionRow>
          <ButtonItem layout="below" onClick={onBack}>
            ← Back to Chat
          </ButtonItem>
        </PanelSectionRow>
      </PanelSection>
    </>
  );
};
