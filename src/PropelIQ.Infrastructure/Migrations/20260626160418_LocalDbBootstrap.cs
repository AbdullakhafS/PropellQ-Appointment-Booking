using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace PropelIQ.Infrastructure.Migrations
{
    /// <inheritdoc />
    public partial class LocalDbBootstrap : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "ChatbotPrompts",
                columns: table => new
                {
                    Id = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    PromptVersion = table.Column<string>(type: "nvarchar(20)", maxLength: 20, nullable: false),
                    PromptText = table.Column<string>(type: "nvarchar(max)", nullable: false),
                    EffectiveDate = table.Column<DateTimeOffset>(type: "datetimeoffset", nullable: false),
                    DeprecatedAt = table.Column<DateTimeOffset>(type: "datetimeoffset", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_ChatbotPrompts", x => x.Id);
                });

            migrationBuilder.CreateTable(
                name: "InsurancePlans",
                columns: table => new
                {
                    Id = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    Name = table.Column<string>(type: "nvarchar(200)", maxLength: 200, nullable: false),
                    AliasesRaw = table.Column<string>(type: "nvarchar(max)", nullable: false, defaultValue: ""),
                    MemberIdFormat = table.Column<string>(type: "nvarchar(200)", maxLength: 200, nullable: true),
                    GroupNumberFormat = table.Column<string>(type: "nvarchar(200)", maxLength: 200, nullable: true),
                    CreatedAt = table.Column<DateTimeOffset>(type: "datetimeoffset", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_InsurancePlans", x => x.Id);
                });

            migrationBuilder.CreateTable(
                name: "InsuranceVerificationAudits",
                columns: table => new
                {
                    Id = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    InsuranceVerificationId = table.Column<int>(type: "int", nullable: false),
                    PreviousStatus = table.Column<string>(type: "nvarchar(30)", maxLength: 30, nullable: false),
                    NewStatus = table.Column<string>(type: "nvarchar(30)", maxLength: 30, nullable: false),
                    VerifiedByStaffId = table.Column<int>(type: "int", nullable: false),
                    VerificationMethod = table.Column<string>(type: "nvarchar(30)", maxLength: 30, nullable: false),
                    Notes = table.Column<string>(type: "nvarchar(1000)", maxLength: 1000, nullable: true),
                    VerifiedAt = table.Column<DateTimeOffset>(type: "datetimeoffset", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_InsuranceVerificationAudits", x => x.Id);
                });

            migrationBuilder.CreateTable(
                name: "InsuranceVerifications",
                columns: table => new
                {
                    Id = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    AppointmentId = table.Column<int>(type: "int", nullable: false),
                    PatientId = table.Column<int>(type: "int", nullable: false),
                    ProvidedInsuranceName = table.Column<string>(type: "nvarchar(200)", maxLength: 200, nullable: true),
                    ProvidedMemberId = table.Column<string>(type: "nvarchar(100)", maxLength: 100, nullable: true),
                    ProvidedGroupNumber = table.Column<string>(type: "nvarchar(100)", maxLength: 100, nullable: true),
                    MatchedPlanId = table.Column<int>(type: "int", nullable: true),
                    ConfidenceScore = table.Column<int>(type: "int", nullable: false),
                    VerificationStatus = table.Column<string>(type: "nvarchar(30)", maxLength: 30, nullable: false),
                    Reason = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: true),
                    CheckedBy = table.Column<string>(type: "nvarchar(50)", maxLength: 50, nullable: false, defaultValue: "system"),
                    VerifiedByStaffId = table.Column<int>(type: "int", nullable: true),
                    VerifiedAt = table.Column<DateTimeOffset>(type: "datetimeoffset", nullable: true),
                    CreatedAt = table.Column<DateTimeOffset>(type: "datetimeoffset", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_InsuranceVerifications", x => x.Id);
                });

            migrationBuilder.CreateTable(
                name: "IntakeAllergies",
                columns: table => new
                {
                    Id = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    IntakeId = table.Column<int>(type: "int", nullable: false),
                    AllergenType = table.Column<string>(type: "nvarchar(50)", maxLength: 50, nullable: false),
                    AllergenName = table.Column<string>(type: "nvarchar(255)", maxLength: 255, nullable: false),
                    ReactionType = table.Column<string>(type: "nvarchar(50)", maxLength: 50, nullable: false),
                    ReactionDescription = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: true),
                    Severity = table.Column<string>(type: "nvarchar(20)", maxLength: 20, nullable: true),
                    ConfidenceScore = table.Column<int>(type: "int", nullable: false, defaultValue: 100),
                    CreatedAt = table.Column<DateTimeOffset>(type: "datetimeoffset", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_IntakeAllergies", x => x.Id);
                });

            migrationBuilder.CreateTable(
                name: "IntakeAuditLogs",
                columns: table => new
                {
                    Id = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    IntakeId = table.Column<int>(type: "int", nullable: false),
                    Action = table.Column<string>(type: "nvarchar(20)", maxLength: 20, nullable: false),
                    ChangedField = table.Column<string>(type: "nvarchar(100)", maxLength: 100, nullable: true),
                    OldValue = table.Column<string>(type: "nvarchar(1000)", maxLength: 1000, nullable: true),
                    NewValue = table.Column<string>(type: "nvarchar(1000)", maxLength: 1000, nullable: true),
                    ChangedBy = table.Column<string>(type: "nvarchar(100)", maxLength: 100, nullable: true),
                    Reason = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: true),
                    ChangedAt = table.Column<DateTimeOffset>(type: "datetimeoffset", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_IntakeAuditLogs", x => x.Id);
                });

            migrationBuilder.CreateTable(
                name: "IntakeConversations",
                columns: table => new
                {
                    Id = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    AppointmentId = table.Column<int>(type: "int", nullable: false),
                    PatientId = table.Column<int>(type: "int", nullable: false),
                    Mode = table.Column<string>(type: "nvarchar(20)", maxLength: 20, nullable: false),
                    Transcript = table.Column<string>(type: "nvarchar(max)", nullable: false),
                    ExtractedData = table.Column<string>(type: "nvarchar(max)", nullable: false),
                    ConfidenceScores = table.Column<string>(type: "nvarchar(max)", nullable: false),
                    CompletedAt = table.Column<DateTimeOffset>(type: "datetimeoffset", nullable: true),
                    SwitchedToManualAt = table.Column<DateTimeOffset>(type: "datetimeoffset", nullable: true),
                    CreatedAt = table.Column<DateTimeOffset>(type: "datetimeoffset", nullable: false),
                    MisunderstandingCount = table.Column<int>(type: "int", nullable: false),
                    CurrentStage = table.Column<int>(type: "int", nullable: false, defaultValue: 0)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_IntakeConversations", x => x.Id);
                });

            migrationBuilder.CreateTable(
                name: "IntakeDrafts",
                columns: table => new
                {
                    Id = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    AppointmentId = table.Column<int>(type: "int", nullable: false),
                    PatientId = table.Column<int>(type: "int", nullable: false),
                    Mode = table.Column<string>(type: "nvarchar(20)", maxLength: 20, nullable: false),
                    DataJson = table.Column<string>(type: "nvarchar(max)", nullable: false),
                    SwitchCount = table.Column<int>(type: "int", nullable: false, defaultValue: 0),
                    LastUpdated = table.Column<DateTimeOffset>(type: "datetimeoffset", nullable: false),
                    ExpiresAt = table.Column<DateTimeOffset>(type: "datetimeoffset", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_IntakeDrafts", x => x.Id);
                });

            migrationBuilder.CreateTable(
                name: "IntakeInsurances",
                columns: table => new
                {
                    Id = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    IntakeId = table.Column<int>(type: "int", nullable: false),
                    InsuranceName = table.Column<string>(type: "nvarchar(200)", maxLength: 200, nullable: true),
                    MemberId = table.Column<string>(type: "nvarchar(100)", maxLength: 100, nullable: true),
                    GroupNumber = table.Column<string>(type: "nvarchar(100)", maxLength: 100, nullable: true),
                    PlanName = table.Column<string>(type: "nvarchar(200)", maxLength: 200, nullable: true),
                    VerificationStatus = table.Column<string>(type: "nvarchar(30)", maxLength: 30, nullable: true),
                    ConfidenceScore = table.Column<int>(type: "int", nullable: true),
                    CreatedAt = table.Column<DateTimeOffset>(type: "datetimeoffset", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_IntakeInsurances", x => x.Id);
                });

            migrationBuilder.CreateTable(
                name: "IntakeMedicalHistories",
                columns: table => new
                {
                    Id = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    IntakeId = table.Column<int>(type: "int", nullable: false),
                    ConditionName = table.Column<string>(type: "nvarchar(255)", maxLength: 255, nullable: false),
                    ConditionCode = table.Column<string>(type: "nvarchar(10)", maxLength: 10, nullable: true),
                    DiagnosedDate = table.Column<DateOnly>(type: "date", nullable: true),
                    Status = table.Column<string>(type: "nvarchar(20)", maxLength: 20, nullable: false, defaultValue: "active"),
                    ConfidenceScore = table.Column<int>(type: "int", nullable: false, defaultValue: 100),
                    Notes = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: true),
                    CreatedAt = table.Column<DateTimeOffset>(type: "datetimeoffset", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_IntakeMedicalHistories", x => x.Id);
                });

            migrationBuilder.CreateTable(
                name: "IntakeMedications",
                columns: table => new
                {
                    Id = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    IntakeId = table.Column<int>(type: "int", nullable: false),
                    MedicationName = table.Column<string>(type: "nvarchar(255)", maxLength: 255, nullable: false),
                    Dosage = table.Column<string>(type: "nvarchar(100)", maxLength: 100, nullable: true),
                    Frequency = table.Column<string>(type: "nvarchar(100)", maxLength: 100, nullable: true),
                    Route = table.Column<string>(type: "nvarchar(50)", maxLength: 50, nullable: true),
                    ConfidenceScore = table.Column<int>(type: "int", nullable: false, defaultValue: 100),
                    Notes = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: true),
                    CreatedAt = table.Column<DateTimeOffset>(type: "datetimeoffset", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_IntakeMedications", x => x.Id);
                });

            migrationBuilder.CreateTable(
                name: "IntakeResponses",
                columns: table => new
                {
                    Id = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    AppointmentId = table.Column<int>(type: "int", nullable: false),
                    PatientId = table.Column<int>(type: "int", nullable: false),
                    Mode = table.Column<string>(type: "nvarchar(20)", maxLength: 20, nullable: false),
                    Status = table.Column<string>(type: "nvarchar(20)", maxLength: 20, nullable: false, defaultValue: "completed"),
                    CompletedAt = table.Column<DateTimeOffset>(type: "datetimeoffset", nullable: false),
                    CreatedAt = table.Column<DateTimeOffset>(type: "datetimeoffset", nullable: false),
                    UpdatedAt = table.Column<DateTimeOffset>(type: "datetimeoffset", nullable: false),
                    CreatedByStaffId = table.Column<int>(type: "int", nullable: true),
                    Notes = table.Column<string>(type: "nvarchar(max)", nullable: true),
                    ChiefComplaint = table.Column<string>(type: "nvarchar(max)", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_IntakeResponses", x => x.Id);
                });

            migrationBuilder.CreateIndex(
                name: "IX_ChatbotPrompts_PromptVersion",
                table: "ChatbotPrompts",
                column: "PromptVersion",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_InsurancePlans_Name",
                table: "InsurancePlans",
                column: "Name");

            migrationBuilder.CreateIndex(
                name: "IX_InsuranceVerificationAudits_InsuranceVerificationId",
                table: "InsuranceVerificationAudits",
                column: "InsuranceVerificationId");

            migrationBuilder.CreateIndex(
                name: "IX_InsuranceVerifications_AppointmentId",
                table: "InsuranceVerifications",
                column: "AppointmentId");

            migrationBuilder.CreateIndex(
                name: "IX_InsuranceVerifications_PatientId",
                table: "InsuranceVerifications",
                column: "PatientId");

            migrationBuilder.CreateIndex(
                name: "IX_InsuranceVerifications_VerificationStatus",
                table: "InsuranceVerifications",
                column: "VerificationStatus");

            migrationBuilder.CreateIndex(
                name: "IX_IntakeAllergies_IntakeId",
                table: "IntakeAllergies",
                column: "IntakeId");

            migrationBuilder.CreateIndex(
                name: "IX_IntakeAuditLogs_IntakeId",
                table: "IntakeAuditLogs",
                column: "IntakeId");

            migrationBuilder.CreateIndex(
                name: "IX_IntakeConversations_AppointmentId",
                table: "IntakeConversations",
                column: "AppointmentId");

            migrationBuilder.CreateIndex(
                name: "IX_IntakeConversations_Mode",
                table: "IntakeConversations",
                column: "Mode");

            migrationBuilder.CreateIndex(
                name: "IX_IntakeConversations_PatientId",
                table: "IntakeConversations",
                column: "PatientId");

            migrationBuilder.CreateIndex(
                name: "IX_IntakeDrafts_AppointmentId",
                table: "IntakeDrafts",
                column: "AppointmentId",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_IntakeInsurances_IntakeId",
                table: "IntakeInsurances",
                column: "IntakeId",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_IntakeMedicalHistories_IntakeId",
                table: "IntakeMedicalHistories",
                column: "IntakeId");

            migrationBuilder.CreateIndex(
                name: "IX_IntakeMedications_IntakeId",
                table: "IntakeMedications",
                column: "IntakeId");

            migrationBuilder.CreateIndex(
                name: "IX_IntakeResponses_AppointmentId",
                table: "IntakeResponses",
                column: "AppointmentId");

            migrationBuilder.CreateIndex(
                name: "IX_IntakeResponses_CreatedAt",
                table: "IntakeResponses",
                column: "CreatedAt");

            migrationBuilder.CreateIndex(
                name: "IX_IntakeResponses_PatientId",
                table: "IntakeResponses",
                column: "PatientId");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "ChatbotPrompts");

            migrationBuilder.DropTable(
                name: "InsurancePlans");

            migrationBuilder.DropTable(
                name: "InsuranceVerificationAudits");

            migrationBuilder.DropTable(
                name: "InsuranceVerifications");

            migrationBuilder.DropTable(
                name: "IntakeAllergies");

            migrationBuilder.DropTable(
                name: "IntakeAuditLogs");

            migrationBuilder.DropTable(
                name: "IntakeConversations");

            migrationBuilder.DropTable(
                name: "IntakeDrafts");

            migrationBuilder.DropTable(
                name: "IntakeInsurances");

            migrationBuilder.DropTable(
                name: "IntakeMedicalHistories");

            migrationBuilder.DropTable(
                name: "IntakeMedications");

            migrationBuilder.DropTable(
                name: "IntakeResponses");
        }
    }
}
