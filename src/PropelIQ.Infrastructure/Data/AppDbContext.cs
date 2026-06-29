using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Storage.ValueConversion;
using PropelIQ.Domain.Entities;
using PropelIQ.Domain.Enums;
using PropelIQ.Domain.ValueObjects;
using PropelIQ.Infrastructure.Security;

namespace PropelIQ.Infrastructure.Data;

public sealed class AppDbContext : DbContext
{
    private readonly TranscriptEncryption? _encryption;

    public AppDbContext(DbContextOptions<AppDbContext> options, TranscriptEncryption? encryption = null)
        : base(options)
    {
        _encryption = encryption;
    }

    public DbSet<IntakeConversation> IntakeConversations => Set<IntakeConversation>();
    public DbSet<ChatbotPrompt> ChatbotPrompts => Set<ChatbotPrompt>();
    public DbSet<IntakeDraft> IntakeDrafts => Set<IntakeDraft>();
    public DbSet<InsurancePlan> InsurancePlans => Set<InsurancePlan>();
    public DbSet<InsuranceVerification> InsuranceVerifications => Set<InsuranceVerification>();
    public DbSet<InsuranceVerificationAudit> InsuranceVerificationAudits => Set<InsuranceVerificationAudit>();
    public DbSet<IntakeResponse> IntakeResponses => Set<IntakeResponse>();
    public DbSet<IntakeMedicalHistory> IntakeMedicalHistories => Set<IntakeMedicalHistory>();
    public DbSet<IntakeMedication> IntakeMedications => Set<IntakeMedication>();
    public DbSet<IntakeAllergy> IntakeAllergies => Set<IntakeAllergy>();
    public DbSet<IntakeInsurance> IntakeInsurances => Set<IntakeInsurance>();
    public DbSet<IntakeAuditLog> IntakeAuditLogs => Set<IntakeAuditLog>();
    public DbSet<AppUserAccount> AppUserAccounts => Set<AppUserAccount>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<IntakeConversation>(entity =>
        {
            entity.ToTable("IntakeConversations");
            entity.HasKey(e => e.Id);

            entity.Property(e => e.AppointmentId).IsRequired();
            entity.Property(e => e.PatientId).IsRequired();
            entity.Property(e => e.Mode)
                  .HasConversion<string>()
                  .HasMaxLength(20)
                  .IsRequired();
            entity.Property(e => e.CreatedAt).IsRequired();

            entity.Property(e => e.Transcript)
                  .HasColumnType("nvarchar(max)")
                  .HasConversion(
                      v => EncryptJson(JsonSerializer.Serialize(v, (JsonSerializerOptions?)null)),
                      v => JsonSerializer.Deserialize<List<ConversationMessage>>(DecryptJson(v), (JsonSerializerOptions?)null) ?? new List<ConversationMessage>());

            entity.Property(e => e.ExtractedData)
                  .HasColumnType("nvarchar(max)")
                  .HasConversion(
                      v => JsonSerializer.Serialize(v, (JsonSerializerOptions?)null),
                      v => JsonSerializer.Deserialize<ExtractedIntakeData>(v, (JsonSerializerOptions?)null) ?? ExtractedIntakeData.Empty());

            entity.Property(e => e.ConfidenceScores)
                  .HasColumnType("nvarchar(max)")
                  .HasConversion(
                      v => JsonSerializer.Serialize(v, (JsonSerializerOptions?)null),
                      v => JsonSerializer.Deserialize<ConfidenceScores>(v, (JsonSerializerOptions?)null) ?? ConfidenceScores.Zero());

            entity.Property(e => e.CurrentStage)
                  .HasConversion<int>()
                  .HasColumnType("int")
                .HasDefaultValue(ConversationStage.Greeting);

            entity.HasIndex(e => e.AppointmentId);
            entity.HasIndex(e => e.PatientId);
            entity.HasIndex(e => e.Mode);
        });

        modelBuilder.Entity<ChatbotPrompt>(entity =>
        {
            entity.ToTable("ChatbotPrompts");
            entity.HasKey(e => e.Id);
            entity.Property(e => e.PromptVersion).HasMaxLength(20).IsRequired();
            entity.Property(e => e.PromptText).HasColumnType("nvarchar(max)").IsRequired();
            entity.Property(e => e.EffectiveDate).IsRequired();
            entity.HasIndex(e => e.PromptVersion).IsUnique();
        });

        modelBuilder.Entity<IntakeDraft>(entity =>
        {
            entity.ToTable("IntakeDrafts");
            entity.HasKey(e => e.Id);
            entity.Property(e => e.AppointmentId).IsRequired();
            entity.Property(e => e.PatientId).IsRequired();
            entity.Property(e => e.Mode).HasMaxLength(20).IsRequired();
            entity.Property(e => e.DataJson).HasColumnType("nvarchar(max)").IsRequired();
            entity.Property(e => e.SwitchCount).HasDefaultValue(0);
            entity.Property(e => e.LastUpdated).IsRequired();
            entity.Property(e => e.ExpiresAt).IsRequired();
            entity.HasIndex(e => e.AppointmentId).IsUnique();
        });

        modelBuilder.Entity<InsurancePlan>(entity =>
        {
            entity.ToTable("InsurancePlans");
            entity.HasKey(e => e.Id);
            entity.Property(e => e.Name).HasMaxLength(200).IsRequired();
            entity.Property(e => e.AliasesRaw).HasColumnType("nvarchar(max)").HasDefaultValue(string.Empty);
            entity.Property(e => e.MemberIdFormat).HasMaxLength(200);
            entity.Property(e => e.GroupNumberFormat).HasMaxLength(200);
            entity.Property(e => e.CreatedAt).IsRequired();
            entity.HasIndex(e => e.Name);
        });

        modelBuilder.Entity<InsuranceVerification>(entity =>
        {
            entity.ToTable("InsuranceVerifications");
            entity.HasKey(e => e.Id);
            entity.Property(e => e.AppointmentId).IsRequired();
            entity.Property(e => e.PatientId).IsRequired();
            entity.Property(e => e.ProvidedInsuranceName).HasMaxLength(200);
            entity.Property(e => e.ProvidedMemberId).HasMaxLength(100);
            entity.Property(e => e.ProvidedGroupNumber).HasMaxLength(100);
            entity.Property(e => e.ConfidenceScore).IsRequired();
            entity.Property(e => e.VerificationStatus).HasMaxLength(30).IsRequired();
            entity.Property(e => e.Reason).HasMaxLength(500);
            entity.Property(e => e.CheckedBy).HasMaxLength(50).HasDefaultValue("system");
            entity.Property(e => e.CreatedAt).IsRequired();
            entity.HasIndex(e => e.AppointmentId);
            entity.HasIndex(e => e.PatientId);
            entity.HasIndex(e => e.VerificationStatus);
        });

        modelBuilder.Entity<InsuranceVerificationAudit>(entity =>
        {
            entity.ToTable("InsuranceVerificationAudits");
            entity.HasKey(e => e.Id);
            entity.Property(e => e.InsuranceVerificationId).IsRequired();
            entity.Property(e => e.PreviousStatus).HasMaxLength(30).IsRequired();
            entity.Property(e => e.NewStatus).HasMaxLength(30).IsRequired();
            entity.Property(e => e.VerifiedByStaffId).IsRequired();
            entity.Property(e => e.VerificationMethod).HasMaxLength(30).IsRequired();
            entity.Property(e => e.Notes).HasMaxLength(1000);
            entity.Property(e => e.VerifiedAt).IsRequired();
            entity.HasIndex(e => e.InsuranceVerificationId);
        });

        modelBuilder.Entity<IntakeResponse>(entity =>
        {
            entity.ToTable("IntakeResponses");
            entity.HasKey(e => e.Id);
            entity.Property(e => e.AppointmentId).IsRequired();
            entity.Property(e => e.PatientId).IsRequired();
            entity.Property(e => e.Mode).HasMaxLength(20).IsRequired();
            entity.Property(e => e.Status).HasMaxLength(20).HasDefaultValue("completed").IsRequired();
            entity.Property(e => e.ChiefComplaint).HasColumnType("nvarchar(max)");
            entity.Property(e => e.Notes).HasColumnType("nvarchar(max)");
            entity.Property(e => e.CompletedAt).IsRequired();
            entity.Property(e => e.CreatedAt).IsRequired();
            entity.Property(e => e.UpdatedAt).IsRequired();
            entity.HasIndex(e => e.AppointmentId);
            entity.HasIndex(e => e.PatientId);
            entity.HasIndex(e => e.CreatedAt);
            entity.Ignore(e => e.MedicalHistory);
            entity.Ignore(e => e.Medications);
            entity.Ignore(e => e.Allergies);
            entity.Ignore(e => e.InsuranceInfo);
        });

        modelBuilder.Entity<IntakeMedicalHistory>(entity =>
        {
            entity.ToTable("IntakeMedicalHistories");
            entity.HasKey(e => e.Id);
            entity.Property(e => e.IntakeId).IsRequired();
            entity.Property(e => e.ConditionName).HasMaxLength(255).IsRequired();
            entity.Property(e => e.ConditionCode).HasMaxLength(10);
            entity.Property(e => e.Status).HasMaxLength(20).HasDefaultValue("active");
            entity.Property(e => e.ConfidenceScore).HasDefaultValue(100);
            entity.Property(e => e.Notes).HasMaxLength(500);
            entity.Property(e => e.CreatedAt).IsRequired();
            entity.HasIndex(e => e.IntakeId);
        });

        modelBuilder.Entity<IntakeMedication>(entity =>
        {
            entity.ToTable("IntakeMedications");
            entity.HasKey(e => e.Id);
            entity.Property(e => e.IntakeId).IsRequired();
            entity.Property(e => e.MedicationName).HasMaxLength(255).IsRequired();
            entity.Property(e => e.Dosage).HasMaxLength(100);
            entity.Property(e => e.Frequency).HasMaxLength(100);
            entity.Property(e => e.Route).HasMaxLength(50);
            entity.Property(e => e.ConfidenceScore).HasDefaultValue(100);
            entity.Property(e => e.Notes).HasMaxLength(500);
            entity.Property(e => e.CreatedAt).IsRequired();
            entity.HasIndex(e => e.IntakeId);
        });

        modelBuilder.Entity<IntakeAllergy>(entity =>
        {
            entity.ToTable("IntakeAllergies");
            entity.HasKey(e => e.Id);
            entity.Property(e => e.IntakeId).IsRequired();
            entity.Property(e => e.AllergenType).HasMaxLength(50).IsRequired();
            entity.Property(e => e.AllergenName).HasMaxLength(255).IsRequired();
            entity.Property(e => e.ReactionType).HasMaxLength(50).IsRequired();
            entity.Property(e => e.ReactionDescription).HasMaxLength(500);
            entity.Property(e => e.Severity).HasMaxLength(20);
            entity.Property(e => e.ConfidenceScore).HasDefaultValue(100);
            entity.Property(e => e.CreatedAt).IsRequired();
            entity.HasIndex(e => e.IntakeId);
        });

        modelBuilder.Entity<IntakeInsurance>(entity =>
        {
            entity.ToTable("IntakeInsurances");
            entity.HasKey(e => e.Id);
            entity.Property(e => e.IntakeId).IsRequired();
            entity.Property(e => e.InsuranceName).HasMaxLength(200);
            entity.Property(e => e.MemberId).HasMaxLength(100);
            entity.Property(e => e.GroupNumber).HasMaxLength(100);
            entity.Property(e => e.PlanName).HasMaxLength(200);
            entity.Property(e => e.VerificationStatus).HasMaxLength(30);
            entity.Property(e => e.CreatedAt).IsRequired();
            entity.HasIndex(e => e.IntakeId).IsUnique();
        });

        modelBuilder.Entity<IntakeAuditLog>(entity =>
        {
            entity.ToTable("IntakeAuditLogs");
            entity.HasKey(e => e.Id);
            entity.Property(e => e.IntakeId).IsRequired();
            entity.Property(e => e.Action).HasMaxLength(20).IsRequired();
            entity.Property(e => e.ChangedField).HasMaxLength(100);
            entity.Property(e => e.OldValue).HasMaxLength(1000);
            entity.Property(e => e.NewValue).HasMaxLength(1000);
            entity.Property(e => e.ChangedBy).HasMaxLength(100);
            entity.Property(e => e.Reason).HasMaxLength(500);
            entity.Property(e => e.ChangedAt).IsRequired();
            entity.HasIndex(e => e.IntakeId);
        });

        modelBuilder.Entity<AppUserAccount>(entity =>
        {
            entity.ToTable("AppUserAccounts");
            entity.HasKey(e => e.Id);
            entity.Property(e => e.UserId).HasMaxLength(100).IsRequired();
            entity.Property(e => e.Email).HasMaxLength(320).IsRequired();
            entity.Property(e => e.PasswordHash).HasMaxLength(500).IsRequired();
            entity.Property(e => e.Role).HasMaxLength(30).IsRequired();
            entity.Property(e => e.Status).HasMaxLength(30).IsRequired();
            entity.Property(e => e.CreatedAt).IsRequired();
            entity.Property(e => e.UpdatedAt).IsRequired();
            entity.HasIndex(e => e.UserId).IsUnique();
        });
    }

    private string EncryptJson(string json)
        => _encryption?.Encrypt(json) ?? json;

    private string DecryptJson(string stored)
        => _encryption?.Decrypt(stored) ?? stored;
}
