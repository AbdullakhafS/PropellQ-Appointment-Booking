using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace PropelIQ.Infrastructure.Migrations
{
    /// <inheritdoc />
    public partial class AddInsurancePreCheck : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
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
                constraints: table => table.PrimaryKey("PK_InsurancePlans", x => x.Id));

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
                constraints: table => table.PrimaryKey("PK_InsuranceVerifications", x => x.Id));

            migrationBuilder.CreateIndex(
                name: "IX_InsurancePlans_Name",
                table: "InsurancePlans",
                column: "Name");

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
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(name: "InsuranceVerifications");
            migrationBuilder.DropTable(name: "InsurancePlans");
        }
    }
}
