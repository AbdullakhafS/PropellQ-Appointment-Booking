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
    }

    private string EncryptJson(string json)
        => _encryption?.Encrypt(json) ?? json;

    private string DecryptJson(string stored)
        => _encryption?.Decrypt(stored) ?? stored;
}
