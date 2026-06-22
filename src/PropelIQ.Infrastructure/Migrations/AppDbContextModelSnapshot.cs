using System;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.EntityFrameworkCore.Metadata;
using PropelIQ.Infrastructure.Data;

#nullable disable

namespace PropelIQ.Infrastructure.Migrations
{
    [DbContext(typeof(AppDbContext))]
    partial class AppDbContextModelSnapshot : ModelSnapshot
    {
        protected override void BuildModel(ModelBuilder modelBuilder)
        {
#pragma warning disable 612, 618
            modelBuilder
                .HasAnnotation("ProductVersion", "9.0.0")
                .HasAnnotation("Relational:MaxIdentifierLength", 128);

            SqlServerModelBuilderExtensions.UseIdentityColumns(modelBuilder);

            modelBuilder.Entity("PropelIQ.Domain.Entities.ChatbotPrompt", b =>
            {
                b.Property<int>("Id").ValueGeneratedOnAdd().HasColumnType("int");
                SqlServerPropertyBuilderExtensions.UseIdentityColumn(b.Property<int>("Id"));
                b.Property<DateTimeOffset?>("DeprecatedAt").HasColumnType("datetimeoffset");
                b.Property<DateTimeOffset>("EffectiveDate").IsRequired().HasColumnType("datetimeoffset");
                b.Property<string>("PromptText").IsRequired().HasColumnType("nvarchar(max)");
                b.Property<string>("PromptVersion").IsRequired().HasMaxLength(20).HasColumnType("nvarchar(20)");
                b.HasKey("Id");
                b.HasIndex("PromptVersion").IsUnique();
                b.ToTable("ChatbotPrompts");
            });

            modelBuilder.Entity("PropelIQ.Domain.Entities.IntakeConversation", b =>
            {
                b.Property<int>("Id").ValueGeneratedOnAdd().HasColumnType("int");
                SqlServerPropertyBuilderExtensions.UseIdentityColumn(b.Property<int>("Id"));
                b.Property<int>("AppointmentId").IsRequired().HasColumnType("int");
                b.Property<DateTimeOffset?>("CompletedAt").HasColumnType("datetimeoffset");
                b.Property<string>("ConfidenceScores").IsRequired().HasColumnType("nvarchar(max)");
                b.Property<DateTimeOffset>("CreatedAt").IsRequired().HasColumnType("datetimeoffset");
                b.Property<string>("ExtractedData").IsRequired().HasColumnType("nvarchar(max)");
                b.Property<int>("MisunderstandingCount").HasColumnType("int");
                b.Property<string>("Mode").IsRequired().HasMaxLength(20).HasColumnType("nvarchar(20)");
                b.Property<int>("PatientId").IsRequired().HasColumnType("int");
                b.Property<DateTimeOffset?>("SwitchedToManualAt").HasColumnType("datetimeoffset");
                b.Property<string>("Transcript").IsRequired().HasColumnType("nvarchar(max)");
                b.HasKey("Id");
                b.HasIndex("AppointmentId");
                b.HasIndex("Mode");
                b.HasIndex("PatientId");
                b.ToTable("IntakeConversations");
            });
#pragma warning restore 612, 618
        }
    }
}
