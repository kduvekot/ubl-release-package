<?xml version="1.0" encoding="US-ASCII"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                version="1.0">

<xsl:import href="oasis/oasis-specification-html.xsl"/>

<xsl:param name="html.cellpadding" select="'4pt'"/>

<xsl:template match="appendix" mode="object.title.template">
  <xsl:text>Appendix </xsl:text>
  <xsl:apply-imports/>
</xsl:template>

<xsl:param name="section.label.includes.component.label" select="1"/>

<xsl:param name="toc.section.depth" select="3"/>

<xsl:template match="sectionx" mode="label.markup">
  <xsl:variable name="complete">
    <xsl:apply-imports/>
  </xsl:variable>
  <xsl:choose>
    <xsl:when test="string-length(substring-after($complete,'.'))">
     <xsl:value-of select="substring($complete,1,string-length($complete)-1)"/>
    </xsl:when>
    <xsl:otherwise>
      <xsl:value-of select="$complete"/>
    </xsl:otherwise>
  </xsl:choose>
</xsl:template>

</xsl:stylesheet>