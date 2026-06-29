using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace PropelIQ.Infrastructure.Migrations
{
    /// <inheritdoc />
    public partial class SeedInsurancePlans : Migration
    {
        private static readonly DateTimeOffset Seeded = new DateTimeOffset(2026, 6, 22, 0, 0, 0, TimeSpan.Zero);

        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            static void Add(MigrationBuilder m, int id, string name, string aliases, string memberId, string groupNum) =>
                m.InsertData("InsurancePlans",
                    columns: ["Id", "Name", "AliasesRaw", "MemberIdFormat", "GroupNumberFormat", "CreatedAt"],
                    values: [id, name, aliases, (object)memberId ?? DBNull.Value, (object)groupNum ?? DBNull.Value, Seeded]);

            Add(migrationBuilder, 1,  "Aetna",                    "Aetna Health|Aetna Insurance|Aetna U.S. Healthcare",              @"^[0-9]{8,10}$",         @"^[0-9A-Z]{3,6}$");
            Add(migrationBuilder, 2,  "Blue Cross Blue Shield",   "BCBS|Blue Cross|Anthem Blue Cross|BlueCross BlueShield",          @"^[A-Z0-9]{8,12}$",      @"^[0-9]{4,8}$");
            Add(migrationBuilder, 3,  "UnitedHealth",             "United Healthcare|UHC|United Health|United HealthCare",           @"^[0-9]{10,12}$",        @"^[0-9]{4,8}$");
            Add(migrationBuilder, 4,  "Humana",                   "Humana Health|Humana Insurance",                                  @"^H[0-9]{8,10}$",        @"^[0-9]{4,8}$");
            Add(migrationBuilder, 5,  "Cigna",                    "Cigna Health|Cigna Healthcare",                                   @"^[0-9]{9,11}$",         @"^[0-9A-Z]{4,8}$");
            Add(migrationBuilder, 6,  "Medicare",                 "Medicare Part A|Medicare Part B|Medicare Advantage|CMS",         @"^[0-9A-Z]{11}$",        null);
            Add(migrationBuilder, 7,  "Medicaid",                 "State Medicaid|Medi-Cal|TennCare|Medicaid Plan",                  @"^[0-9A-Z]{8,15}$",      null);
            Add(migrationBuilder, 8,  "Kaiser Permanente",        "Kaiser|KP|Kaiser Health",                                        @"^[0-9]{8,11}$",         @"^[0-9]{4,8}$");
            Add(migrationBuilder, 9,  "Molina Healthcare",        "Molina|Molina Health",                                           @"^[0-9]{9,12}$",         @"^[0-9]{4,8}$");
            Add(migrationBuilder, 10, "Centene",                  "Centene Corporation|WellCare|Ambetter|Health Net",                @"^[0-9A-Z]{8,12}$",      @"^[0-9]{4,8}$");
            Add(migrationBuilder, 11, "Anthem",                   "Anthem Health|Anthem BCBS|Anthem Inc",                           @"^[A-Z0-9]{8,12}$",      @"^[0-9]{4,8}$");
            Add(migrationBuilder, 12, "CVS Health",               "CVS Caremark|Aetna CVS|CVS Pharmacy",                            @"^[0-9A-Z]{9,12}$",      @"^[0-9A-Z]{3,8}$");
            Add(migrationBuilder, 13, "Elevance Health",          "Elevance|Wellpoint",                                             @"^[A-Z0-9]{8,12}$",      @"^[0-9]{4,8}$");
            Add(migrationBuilder, 14, "Oscar Health",             "Oscar|Oscar Insurance",                                          @"^[0-9]{8,10}$",         @"^[0-9]{4,8}$");
            Add(migrationBuilder, 15, "Bright Health",            "Bright Health Plan|Bright Healthcare",                           @"^[0-9A-Z]{8,11}$",      @"^[0-9]{4,8}$");
            Add(migrationBuilder, 16, "Ambetter",                 "Ambetter Health|Ambetter from Sunshine",                         @"^[0-9A-Z]{8,12}$",      @"^[0-9]{4,8}$");
            Add(migrationBuilder, 17, "TRICARE",                  "Tricare Prime|Tricare Select|Military Health",                   @"^[0-9]{9,11}$",         @"^[0-9A-Z]{4,8}$");
            Add(migrationBuilder, 18, "Veterans Affairs",         "VA|VA Health|Department of Veterans Affairs",                    @"^[0-9]{8,10}$",         null);
            Add(migrationBuilder, 19, "Magellan Health",          "Magellan|Magellan Complete Care",                                @"^[0-9A-Z]{8,12}$",      @"^[0-9]{4,8}$");
            Add(migrationBuilder, 20, "WellCare",                 "WellCare Health|WellCare by Centene",                            @"^[0-9A-Z]{8,12}$",      @"^[0-9]{4,8}$");
            Add(migrationBuilder, 21, "Geisinger",                "Geisinger Health Plan|Geisinger Medical",                        @"^G[0-9]{7,10}$",        @"^[0-9]{4,8}$");
            Add(migrationBuilder, 22, "Harvard Pilgrim",          "Harvard Pilgrim Health Care|HP Health",                          @"^[A-Z][0-9]{7,10}$",    @"^[0-9]{4,8}$");
            Add(migrationBuilder, 23, "Tufts Health Plan",        "Tufts|Tufts Associated Health Plans",                            @"^[0-9A-Z]{8,12}$",      @"^[0-9]{4,8}$");
            Add(migrationBuilder, 24, "Priority Health",          "Priority Health Michigan",                                       @"^[0-9]{9,11}$",         @"^[0-9]{4,8}$");
            Add(migrationBuilder, 25, "Premera",                  "Premera Blue Cross|Premera Health",                              @"^[A-Z0-9]{8,12}$",      @"^[0-9]{4,8}$");
            Add(migrationBuilder, 26, "Regence",                  "Regence BlueShield|Regence BlueCross",                           @"^[A-Z0-9]{8,12}$",      @"^[0-9]{4,8}$");
            Add(migrationBuilder, 27, "HealthMarket",             "HealthMarket Insurance|HealthMarkets",                           @"^[0-9A-Z]{8,12}$",      @"^[0-9A-Z]{4,8}$");
            Add(migrationBuilder, 28, "Coventry Health",          "Coventry|Coventry Healthcare",                                   @"^[0-9]{9,12}$",         @"^[0-9]{4,8}$");
            Add(migrationBuilder, 29, "Guardian",                 "Guardian Life|Guardian Insurance|The Guardian",                  @"^[0-9]{8,11}$",         @"^[0-9A-Z]{4,8}$");
            Add(migrationBuilder, 30, "MetLife",                  "MetLife Health|Metropolitan Life",                               @"^[0-9A-Z]{8,12}$",      @"^[0-9A-Z]{4,8}$");
            Add(migrationBuilder, 31, "Sun Life",                 "Sun Life Financial|Sun Life Insurance",                          @"^[0-9A-Z]{8,12}$",      @"^[0-9A-Z]{4,8}$");
            Add(migrationBuilder, 32, "BCBS Alabama",             "Blue Cross Blue Shield of Alabama",                              @"^[A-Z0-9]{8,12}$",      @"^[0-9]{4,8}$");
            Add(migrationBuilder, 33, "BCBS Florida",             "Florida Blue|Blue Cross Blue Shield of Florida",                 @"^[A-Z0-9]{8,12}$",      @"^[0-9]{4,8}$");
            Add(migrationBuilder, 34, "BCBS Texas",               "Blue Cross Blue Shield of Texas|BCBS TX",                        @"^[A-Z0-9]{8,12}$",      @"^[0-9]{4,8}$");
            Add(migrationBuilder, 35, "BCBS Illinois",            "HCSC|Blue Cross Blue Shield of Illinois",                        @"^[A-Z0-9]{8,12}$",      @"^[0-9]{4,8}$");
            Add(migrationBuilder, 36, "BCBS Michigan",            "Blue Cross Blue Shield of Michigan",                             @"^[A-Z0-9]{8,12}$",      @"^[0-9]{4,8}$");
            Add(migrationBuilder, 37, "Highmark",                 "Highmark Blue Cross|Highmark Health",                            @"^[A-Z0-9]{8,12}$",      @"^[0-9]{4,8}$");
            Add(migrationBuilder, 38, "Independence Blue Cross",  "Independence BC|IBCBS",                                          @"^[A-Z0-9]{8,12}$",      @"^[0-9]{4,8}$");
            Add(migrationBuilder, 39, "EmblemHealth",             "EmblemHealth GHI|HIP Health Plan",                               @"^[0-9A-Z]{8,12}$",      @"^[0-9]{4,8}$");
            Add(migrationBuilder, 40, "Carefirst",                "CareFirst BlueCross BlueShield",                                 @"^[A-Z0-9]{8,12}$",      @"^[0-9]{4,8}$");
            Add(migrationBuilder, 41, "Health Alliance",          "Health Alliance Medical Plans|HAMP",                             @"^[0-9A-Z]{8,12}$",      @"^[0-9]{4,8}$");
            Add(migrationBuilder, 42, "SelectHealth",             "SelectHealth Utah|SelectHealth Inc",                             @"^[0-9A-Z]{9,12}$",      @"^[0-9]{4,8}$");
            Add(migrationBuilder, 43, "MVP Health Care",          "MVP Health|MVP Health Plan",                                     @"^[0-9A-Z]{8,12}$",      @"^[0-9]{4,8}$");
            Add(migrationBuilder, 44, "Capital BlueCross",        "Capital Blue Cross",                                             @"^[A-Z0-9]{8,12}$",      @"^[0-9]{4,8}$");
            Add(migrationBuilder, 45, "Community Health Plan",    "CHP|Community Health Plan of Washington",                        @"^[0-9A-Z]{8,12}$",      @"^[0-9]{4,8}$");
            Add(migrationBuilder, 46, "CHIP",                     "Children's Health Insurance Program|Child Health Plus",          @"^[0-9A-Z]{8,15}$",      null);
            Add(migrationBuilder, 47, "HealthSpring",             "HealthSpring Tennessee|Cigna HealthSpring",                      @"^[0-9A-Z]{8,12}$",      @"^[0-9]{4,8}$");
            Add(migrationBuilder, 48, "Horizon BCBS",             "Horizon Blue Cross Blue Shield of New Jersey|Horizon NJ",       @"^[A-Z0-9]{8,12}$",      @"^[0-9]{4,8}$");
            Add(migrationBuilder, 49, "Providence Health Plan",   "Providence Health|Providence Health Assurance",                  @"^[0-9A-Z]{8,12}$",      @"^[0-9]{4,8}$");
            Add(migrationBuilder, 50, "Point32Health",            "Tufts Health Plan|Harvard Pilgrim|Point32",                      @"^[0-9A-Z]{8,12}$",      @"^[0-9]{4,8}$");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DeleteData("InsurancePlans", "Id", Enumerable.Range(1, 50).Cast<object>().ToArray());
        }
    }
}
