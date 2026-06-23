using System.Text.RegularExpressions;
using PropelIQ.Domain.Entities;

namespace PropelIQ.Infrastructure.Insurance;

/// <summary>
/// Pure-logic engine: matches a submitted insurance name/ID against a plan list and computes a confidence score.
/// No I/O — fully unit-testable in isolation.
/// </summary>
public static class InsuranceMatcher
{
    public const int ThresholdVerified = 70;

    public sealed record MatchResult(
        InsurancePlan? MatchedPlan,
        int ConfidenceScore,
        string VerificationStatus,
        string Reason
    );

    /// <summary>
    /// Computes a confidence score (0–100) and verification status for the provided insurance fields
    /// against the supplied plan list.
    /// </summary>
    public static MatchResult Evaluate(
        string? insuranceName,
        string? memberId,
        string? groupNumber,
        IReadOnlyList<InsurancePlan> plans)
    {
        // --- Step 1: match plan by name / alias ---
        var matched = FindPlan(insuranceName, plans);

        if (matched is null)
        {
            return new MatchResult(
                null, 0, "unverified",
                string.IsNullOrWhiteSpace(insuranceName)
                    ? "No insurance name provided."
                    : "Insurance plan not recognised.");
        }

        // --- Step 2: member ID validation ---
        int confidence;
        string reason;

        if (string.IsNullOrWhiteSpace(memberId))
        {
            confidence = 50;
            reason = $"Plan '{matched.Name}' recognised but no member ID provided.";
        }
        else if (matched.MemberIdFormat is not null && !Matches(memberId, matched.MemberIdFormat))
        {
            confidence = 50;
            reason = $"Plan '{matched.Name}' recognised but member ID format does not match expected pattern.";
        }
        else
        {
            confidence = 100;
            reason = $"Plan '{matched.Name}' recognised and member ID format is valid.";
        }

        // --- Step 3: group number validation (optional deduction) ---
        if (!string.IsNullOrWhiteSpace(groupNumber)
            && matched.GroupNumberFormat is not null
            && !Matches(groupNumber, matched.GroupNumberFormat))
        {
            confidence = Math.Max(0, confidence - 20);
            reason += " Group number format is invalid.";
        }

        // --- Step 4: clamp and assign status ---
        confidence = Math.Clamp(confidence, 0, 100);
        var status = confidence >= ThresholdVerified ? "verified" : "unverified";

        return new MatchResult(matched, confidence, status, reason.Trim());
    }

    private static InsurancePlan? FindPlan(string? name, IReadOnlyList<InsurancePlan> plans)
    {
        if (string.IsNullOrWhiteSpace(name)) return null;
        var normalised = name.Trim();

        // 1. Exact name match
        var exact = plans.FirstOrDefault(p =>
            p.Name.Equals(normalised, StringComparison.OrdinalIgnoreCase));
        if (exact is not null) return exact;

        // 2. Alias exact match
        var alias = plans.FirstOrDefault(p =>
            p.Aliases.Any(a => a.Equals(normalised, StringComparison.OrdinalIgnoreCase)));
        if (alias is not null) return alias;

        // 3. Partial: plan name starts-with or contains the input, or vice-versa
        var partial = plans.FirstOrDefault(p =>
            p.Name.Contains(normalised, StringComparison.OrdinalIgnoreCase) ||
            normalised.Contains(p.Name, StringComparison.OrdinalIgnoreCase) ||
            p.Aliases.Any(a =>
                a.Contains(normalised, StringComparison.OrdinalIgnoreCase) ||
                normalised.Contains(a, StringComparison.OrdinalIgnoreCase)));

        return partial;
    }

    private static bool Matches(string value, string pattern)
    {
        try { return Regex.IsMatch(value.Trim(), pattern, RegexOptions.None, TimeSpan.FromMilliseconds(100)); }
        catch { return false; }
    }
}
