<?xml version="1.0" encoding="UTF-8"?>
<schema xmlns="http://purl.oclc.org/dsdl/schematron" queryBinding="xslt2">
   <ns prefix="cbc"
       uri="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"/>
   <ns prefix="ext"
       uri="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"/>
   <!--
A set of Schematron rules against which UBL 2.5 document constraints are
tested in the scope of a second pass validation after schema validation
has been performed.

Required namespace declarations as indicated in this set of rules:

<ns prefix="ext" uri="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"/>
<ns prefix="cbc" uri="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"/>

The following is a summary of the additional document constraints:

[IND1] All UBL instance documents SHALL validate to a corresponding schema.

 - this is tested in the first pass by schema validation, not in the second
   pass with Schematron validation

[IND2] All UBL instance documents SHALL identify their character encoding
       within the XML declaration.

 - this cannot be tested using Schematron as the information is not part of
   XDM (the XML Data Model)

[IND3] In conformance with ISO IEC ITU UN/CEFACT eBusiness Memorandum of
       Understanding Management Group (MOUMG) Resolution 01/08 (MOU/MG01n83)
       as agreed to by OASIS, all UBL XML SHOULD be expressed using UTF-8.

 - this cannot be tested using Schematron as the information is not part of
   XDM (the XML Data Model)

[IND4] (This archaic test no longer exists)

[IND5] UBL-conforming instance documents SHALL NOT contain an element devoid of content or containing null values.

 - implemented below
 - per the documentation, this does not apply to the arbitrary content of
   an extension

[IND6] The absence of a construct or data in a UBL instance document SHALL NOT carry meaning.

 - this cannot be tested using Schematron as it is an application constraint
   on the interpretation of the document

[IND7] Where two or more sibling “Text. Type” elements of the same name exist in a document, no two can have the same “languageID” attribute value.

 - implemented below

[IND8] Where two or more sibling “Text. Type” elements of the same name exist in a document, no two can omit the “languageID” attribute.

 - implemented below

[IND9] UBL-conforming instance documents SHALL NOT contain an attribute devoid of content or containing null values.

 - implemented below
 - per the documentation, this does not apply to the arbitrary content of
   an extension
      -->
   <pattern>
      <rule context="ext:*"><!--no constraints for extension elements-->
         <report test="false()"/>
      </rule>
      <rule context="ext:*//*"><!--no constraints in extension elements-->
         <report test="false()"/>
      </rule>
      <rule context="*[not(*)]">
         <assert test="normalize-space(.)">UBL rule [IND5] states that elements cannot be void of content.
</assert>
      </rule>
   </pattern>
   <pattern>
      <rule context="@*[normalize-space(.)='']">
         <assert test="normalize-space(.)">UBL rule [IND5] infers that attributes cannot be void of content.
</assert>
      </rule>
   </pattern>
   <pattern>
      <rule context="*[@languageID]">
         <assert test="not(../*[name(.)=name(current())]                           [generate-id(.)!=generate-id(current())]                           [string(@languageID)=string(current()/@languageID)])">UBL rule [IND7] states that two sibling elements of the same name cannot have the same languageID= attribute value
</assert>
      </rule>
      <rule context="cbc:AcceptedVariantsDescription | cbc:AccountingCost | cbc:ActivityType | cbc:AdditionalConditions | cbc:AdditionalInformation | cbc:AdditionalMattersDescription | cbc:AllowanceChargeReason | cbc:AnnotationContent | cbc:AntennaLocus | cbc:ApplicableCategory | cbc:ApprovalStatus | cbc:Article | cbc:AwardingCriterionDescription | cbc:BackorderReason | cbc:BuildingNumber | cbc:BuyerReference | cbc:CalculationExpression | cbc:CandidateStatement | cbc:CanonicalizationMethod | cbc:CargoAndBallastTankConditionDescription | cbc:CarrierServiceInstructions | cbc:CertificateType | cbc:CertificationLevelDescription | cbc:ChangeConditions | cbc:Channel | cbc:Characteristics | cbc:CodeValue | cbc:Comment | cbc:CompanyLegalForm | cbc:Condition | cbc:Conditions | cbc:ConditionsDescription | cbc:ConsumersEnergyLevel | cbc:ConsumptionLevel | cbc:ConsumptionType | cbc:Content | cbc:ContractSubdivision | cbc:ContractType | cbc:CorrectionType | cbc:CountrySubentity | cbc:CourseOverGroundDirection | cbc:CriterionDescription | cbc:CurrentChargeType | cbc:CustomerReference | cbc:CustomsClearanceServiceInstructions | cbc:DamageRemarks | cbc:DataSendingCapability | cbc:DeliveryInstructions | cbc:DemurrageInstructions | cbc:Department | cbc:Description | cbc:DistributionType | cbc:District | cbc:DocumentDescription | cbc:DocumentHash | cbc:DocumentType | cbc:Duty | cbc:EffectDescription | cbc:ElectronicDeviceDescription | cbc:ElectronicMail | cbc:EmbeddedDocument | cbc:EmissionFactorSource | cbc:EmissionStandardReference | cbc:EstimatedTimingFurtherPublication | cbc:ExclusionReason | cbc:ExemptionReason | cbc:ExpectedDescription | cbc:Expression | cbc:Extension | cbc:FeeDescription | cbc:Floor | cbc:ForwarderServiceInstructions | cbc:Frequency | cbc:FuelType | cbc:FundingProgram | cbc:GivenTreatmentDescription | cbc:GroupType | cbc:GroupingLots | cbc:HandlingInstructions | cbc:HashAlgorithmMethod | cbc:HaulageInstructions | cbc:HeatingType | cbc:ISSCAbsenceReason | cbc:Information | cbc:InhouseMail | cbc:InstructionNote | cbc:Instructions | cbc:InsuranceTypeDescription | cbc:InvoicingPartyReference | cbc:JobTitle | cbc:JurisdictionLevel | cbc:Justification | cbc:JustificationDescription | cbc:Keyword | cbc:LatestMeterReadingMethod | cbc:LegalReference | cbc:LifecycleStageDescription | cbc:LimitationDescription | cbc:Line | cbc:ListValue | cbc:Location | cbc:Login | cbc:LossRisk | cbc:LowTendersDescription | cbc:MaintenanceFrequencyDescription | cbc:MarkAttention | cbc:MarkCare | cbc:MaximumValue | cbc:MessageFormat | cbc:MeterConstant | cbc:MeterNumber | cbc:MeterReadingComments | cbc:MeterReadingType | cbc:MinimumImprovementBid | cbc:MinimumValue | cbc:ModificationReasonDescription | cbc:MonetaryScope | cbc:MovieTitle | cbc:NameSuffix | cbc:NatureOfIllnessDescription | cbc:NegotiationDescription | cbc:NoControlActionsReason | cbc:Note | cbc:OfficialUse | cbc:OneTimeChargeType | cbc:OptionsDescription | cbc:OrderableUnit | cbc:OrganizationDepartment | cbc:OtherControlActions | cbc:OutstandingReason | cbc:PackagingType | cbc:PackingMaterial | cbc:PartyType | cbc:Password | cbc:PayPerView | cbc:PaymentDescription | cbc:PaymentMeansDescription | cbc:PaymentNote | cbc:PersonalSituation | cbc:PhoneNumber | cbc:PlacardEndorsement | cbc:PlacardNotation | cbc:PlannedInspectionsDescription | cbc:PlannedOperationsDescription | cbc:PlannedWorksDescription | cbc:PlotIdentification | cbc:PostalZone | cbc:Postbox | cbc:PreviousMeterReadingMethod | cbc:PriceChangeReason | cbc:PriceRevisionFormulaDescription | cbc:PriceType | cbc:PrintQualifier | cbc:Priority | cbc:PrizeDescription | cbc:ProcessDescription | cbc:ProcessReason | cbc:ProcurementType | cbc:Purpose | cbc:PurposeType | cbc:Rank | cbc:RecurringProcurementDescription | cbc:Reference | cbc:ReferencedDocumentInternalAddress | cbc:Region | cbc:RegistrationNationality | cbc:RejectReason | cbc:Remarks | cbc:ReplenishmentOwnerDescription | cbc:RepresentationType | cbc:ResidenceType | cbc:Resolution | cbc:ResourceOriginDescription | cbc:Response | cbc:RoleDescription | cbc:Room | cbc:SealingPartyType | cbc:ServiceNumberCalled | cbc:ServiceType | cbc:ShipmentStageType | cbc:ShippingMarks | cbc:ShipsRequirements | cbc:SickAnimalDescription | cbc:SignatureMethod | cbc:SpecialInstructions | cbc:SpecialServiceInstructions | cbc:SpecialTerms | cbc:SpecialTransportRequirements | cbc:StatusReason | cbc:StowawayDescription | cbc:SubTypeDescription | cbc:Subject | cbc:SubscriberType | cbc:SummaryDescription | cbc:TariffDescription | cbc:TaxExemptionReason | cbc:TechnicalCommitteeDescription | cbc:TelecommunicationsServiceCall | cbc:TelecommunicationsServiceCategory | cbc:TelecommunicationsSupplyType | cbc:Telefax | cbc:Telephone | cbc:TestMethod | cbc:Text | cbc:TierRange | cbc:TimeAmount | cbc:TimezoneOffset | cbc:TimingComplaint | cbc:Title | cbc:TradingRestrictions | cbc:TransitDescription | cbc:TransportServiceProviderSpecialTerms | cbc:TransportUserSpecialTerms | cbc:TransportationServiceDescription | cbc:UNPackingGroup | cbc:ValidateProcess | cbc:ValidateTool | cbc:ValidateToolVersion | cbc:Value | cbc:ValueQualifier | cbc:WarrantyInformation | cbc:WasteTypeDescription | cbc:WeighingDeviceType | cbc:Weight | cbc:WeightingConsiderationDescription | cbc:WorkItemDescription | cbc:WorkPhase | cbc:WorkTypeDescription | cbc:XPath">
         <assert test="not(../*[name(.)=name(current())]                                   [generate-id(.)!=generate-id(current())]                                   [not(@languageID)])">UBL rule [IND8] states that two sibling elements of the same name cannot both omit the languageID= attribute
</assert>
      </rule>
   </pattern>
</schema>
