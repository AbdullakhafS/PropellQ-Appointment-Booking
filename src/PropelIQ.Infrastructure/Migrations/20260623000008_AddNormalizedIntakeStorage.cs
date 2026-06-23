using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace PropelIQ.Infrastructure.Migrations
{
    /// <inheritdoc />
    public partial class AddNormalizedIntakeStorage : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
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
                    ChiefComplaint = table.Column<string>(type: "nvarchar(max)", nullable: true),
                    Notes = table.Column<string>(type: "nvarchar(max)", nullable: true),
                    CompletedAt = table.Column<DateTimeOffset>(type: "datetimeoffset", nullable: false),
                    CreatedAt = table.Column<DateTimeOffset>(type: "datetimeoffset", nullable: false),
                    UpdatedAt = table.Column<DateTimeOffset>(type: "datetimeoffset", nullable: false),
                    CreatedByStaffId = table.Column<int>(type: "int", nullable: true)
                },
                constraints: table => table.PrimaryKey("PK_IntakeResponses", x => x.Id));

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
                constraints: table => table.PrimaryKey("PK_IntakeMedicalHistories", x => x.Id));

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
                constraints: table => table.PrimaryKey("PK_IntakeMedications", x => x.Id));

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
                constraints: table => table.PrimaryKey("PK_IntakeAllergies", x => x.Id));

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
                constraints: table => table.PrimaryKey("PK_IntakeInsurances", x => x.Id));

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
                constraints: table => table.PrimaryKey("PK_IntakeAuditLogs", x => x.Id));

            // Indexes
            foreach (var (table, col) in new[]
            {
                ("IntakeResponses", "AppointmentId"),
                ("IntakeResponses", "PatientId"),
                ("IntakeResponses", "CreatedAt"),
                ("IntakeMedicalHistories", "IntakeId"),
                ("IntakeMedications", "IntakeId"),
                ("IntakeAllergies", "IntakeId"),
                ("IntakeAuditLogs", "IntakeId"),
            })
            {
                migrationBuilder.CreateIndex($"IX_{table}_{col}", table, col);
            }

            migrationBuilder.CreateIndex("IX_IntakeInsurances_IntakeId", "IntakeInsurances", "IntakeId", unique: true);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            foreach (var table in new[] { "IntakeAuditLogs", "IntakeInsurances", "IntakeAllergies", "IntakeMedications", "IntakeMedicalHistories", "IntakeResponses" })
                migrationBuilder.DropTable(table);
        }
    }
}
