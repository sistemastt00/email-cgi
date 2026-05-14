"""handlers/email_templates.py — Blueprint-exact branded email HTML builder."""

_CDN  = "https://holcqv.stripocdn.email/content/guids/"
_C919 = _CDN + "CABINET_919ce8fd7f58c2840e854953c4ed3c482eae34e1c2343e5f2a9178c0f557e6ec/images/"

BANNER_TICKET      = _CDN + "CABINET_222641a5fbc95de18f4b301f08ca1015938bea668b050ddba2d02353f876cd96/images/image_Azl.jpeg"
BANNER_AGENDAR     = _CDN + "CABINET_6d29a95d10498e70aa1d0b8ac7aadb56f482e88409660201ce637de429c40c32/images/1_bO3.png"
BANNER_RESERVAR    = _CDN + "CABINET_abeabb86ddc4b1cad385b8b0553ef6e35127b66b88dee696959f17e7bc2e5fa0/images/2.png"
BANNER_INCIDENCIA  = _CDN + "CABINET_a3b40f001fa349afb86ee2ba08be2da85a1a217164be1535fe1f91bedb02d4c6/images/4.png"
BANNER_AUTORIZAR   = _CDN + "CABINET_0f5d17d0884b2fce1cd43eb2989c2d053e172c12568b5acb58eb2afb7ffc84e7/images/3.png"
BANNER_ACTUALIZAR  = _CDN + "CABINET_c2d0fc0bd401f34b46860c5a950552f0ba06d0b7f68affcbb243754bbfe27789/images/6.png"
BANNER_INVENTARIO  = _CDN + "CABINET_db934d944ba9e5cadebd098e9f12921ef69460ab32ee9ea470a7d5b628748570/images/7.png"
BANNER_VALORACION  = _CDN + "CABINET_3768f904ca149dde47224f759bb7b88eeefe941e39f6db427fb69b4dbde34931/images/8.png"
BANNER_PRESUPUESTO = _CDN + "CABINET_2f9f950a9f35bbc1fccb309677970421532c7f6bc06a661e4ea0c41c62a80fcd/images/tu_trastero_1.png"
BANNER_AREA_CLI    = _CDN + "CABINET_df92a44af559890a288d1cd2e42ba9e8c251ef1eb08489d652f46b998e9e619f/images/11.png"
BANNER_MUDANZA_IMG = _CDN + "CABINET_214cd02da279ba7d04f98e91b65a16e515f8f4df164aae07dd19a0811f5b2ba1/images/mudanza.png"
BANNER_MOROSO      = _CDN + "CABINET_2c543671a24db6334cbc7268d334adccc23819ed471b0c823462ef6379abd91a/images/tu_trastero_2.png"
BANNER_DESESTIMA   = _CDN + "CABINET_abeabb86ddc4b1cad385b8b0553ef6e35127b66b88dee696959f17e7bc2e5fa0/images/tu_trastero_5.png"

_MUDANZA_URL = "https://tutrastero.com/es/productos/empresa-de-mudanzas-en-madrid/"
_MUDANZA_CS  = _C919 + "tutrasteromudanzasycajasdecartonemail_oJe.jpg"
_ANIV_CS     = _C919 + "tutrastero20aniversario_QCO.jpg"
_LOGO        = _C919 + "tutrasterologocabeceraemail_Xa3.jpg"

_P  = 'style="Margin:0;mso-line-height-rule:exactly;font-family:arial,\'helvetica neue\',helvetica,sans-serif;line-height:21px;letter-spacing:0;color:#333333;font-size:14px;text-align:justify"'
_PL = 'style="Margin:0;mso-line-height-rule:exactly;font-family:arial,\'helvetica neue\',helvetica,sans-serif;line-height:21px;letter-spacing:0;color:#333333;font-size:14px"'
_PT = 'style="Margin:0;mso-line-height-rule:exactly;font-family:arial,\'helvetica neue\',helvetica,sans-serif;line-height:27px;letter-spacing:0;color:#333333;font-size:14px"'


def dark_btn(url: str, text: str) -> str:
    return (
        f'<span class="es-button-border" style="border-style:solid;border-color:#333333;background:#333333;'
        f'border-width:2px;display:inline-block;border-radius:5px;width:auto">'
        f'<a href="{url}" target="_blank" class="es-button" style="mso-style-priority:100 !important;'
        f'text-decoration:none !important;mso-line-height-rule:exactly;color:#ffffff;font-size:22px;'
        f'padding:20px;display:inline-block;background:#333333;border-radius:5px;'
        f'font-family:arial,\'helvetica neue\',helvetica,sans-serif;font-weight:bold;font-style:normal;'
        f'line-height:26.4px;width:auto;text-align:center;letter-spacing:0;'
        f'mso-padding-alt:0;mso-border-alt:10px solid #333333">{text}</a></span>'
    )


def light_btn(url: str, text: str) -> str:
    return (
        f'<span class="es-button-border" style="border-style:solid;border-color:#333333;background:#efefef;'
        f'border-width:2px;display:inline-block;border-radius:5px;width:auto">'
        f'<a href="{url}" target="_blank" class="es-button" style="mso-style-priority:100 !important;'
        f'text-decoration:none !important;mso-line-height-rule:exactly;color:#000000;font-size:22px;'
        f'padding:20px;display:inline-block;background:#efefef;border-radius:5px;'
        f'font-family:arial,\'helvetica neue\',helvetica,sans-serif;font-weight:bold;font-style:normal;'
        f'line-height:26.4px;width:auto;text-align:center;letter-spacing:0;'
        f'mso-padding-alt:0;mso-border-alt:10px solid #efefef">{text}</a></span>'
    )


def build(
    title: str,
    banner_url: str,
    body_html: str,
    cta_html: str = "",
    after_btn_html: str = "",
    is_ticket: bool = False,
) -> str:
    """Assemble blueprint-exact branded email HTML."""

    # Banner section — gray bg for CTA emails, plain white for ticket emails
    if is_ticket:
        banner_td_attr = 'style="padding:10px;Margin:0"'
        banner_img     = f'<img src="{banner_url}" alt="" height="305" class="adapt-img" style="display:block;font-size:14px;border:0;outline:none;text-decoration:none;margin:0">'
    else:
        banner_td_attr = 'bgcolor="#f2f2f2" style="padding:10px;Margin:0;background-color:#f2f2f2"'
        banner_img     = f'<img src="{banner_url}" alt="" width="580" class="adapt-img" style="display:block;font-size:14px;border:0;outline:none;text-decoration:none">'

    # Body cell style differs between ticket and CTA
    if is_ticket:
        body_cell_attr = 'align="left" class="es-text-6340" style="padding:20px;Margin:0"'
    else:
        body_cell_attr = 'align="left" style="Margin:0;padding-right:20px;padding-left:20px;padding-bottom:20px;padding-top:40px"'

    # CTA + after-button + separator + cross-sell block
    if cta_html:
        cta_block = f"""
                    <tr>
                     <td align="center" style="padding:0;Margin:0">{cta_html}</td>
                    </tr>
                    <tr>
                     <td align="center" style="padding:25px;Margin:0;font-size:0">
                      <table border="0" width="100%" height="100%" cellpadding="0" cellspacing="0" role="presentation" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px">
                       <tr><td style="padding:0;Margin:0;margin:0px;border-bottom:0px solid #cccccc;background:unset;height:0px;width:100%"></td></tr>
                      </table>
                     </td>
                    </tr>"""
        if after_btn_html:
            cta_block += f"""
                    <tr>
                     <td align="left" style="Margin:0;padding-right:20px;padding-left:20px;padding-top:40px;padding-bottom:30px">{after_btn_html}</td>
                    </tr>"""
    else:
        cta_block = ""

    # Separator + cross-sell (always present)
    crosssell_block = f"""
                   <tr>
                    <td align="left" style="padding:0;Margin:0;width:560px">
                     <table cellpadding="0" cellspacing="0" width="100%" role="presentation" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px">
                      <tr>
                       <td align="center" style="padding:20px;Margin:0;font-size:0">
                        <table width="100%" height="100%" cellpadding="0" cellspacing="0" border="0" class="es-spacer" role="presentation" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px">
                         <tr><td style="padding:0;Margin:0;background:none;height:0px;width:100%;margin:0px;border-bottom:1px solid #cccccc"></td></tr>
                        </table>
                       </td>
                      </tr>
                     </table>
                    </td>
                   </tr>
                   <tr>
                    <td align="left" style="padding:0;Margin:0;width:560px">
                     <table width="100%" cellpadding="0" cellspacing="0" role="presentation" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px">
                      <tr>
                       <td align="center" style="padding:0;Margin:0;font-size:0px"><a target="_blank" href="{_MUDANZA_URL}" style="mso-line-height-rule:exactly;text-decoration:underline;color:#5C68E2;font-size:14px"><img src="{_MUDANZA_CS}" alt="&#xBF;Necesitas hacer una mudanza?" width="560" title="&#xBF;Necesitas hacer una mudanza?" class="adapt-img" style="display:block;font-size:14px;border:0;outline:none;text-decoration:none"></a></td>
                      </tr>
                      <tr>
                       <td align="center" style="padding:25px;Margin:0;font-size:0">
                        <table width="100%" height="100%" cellpadding="0" cellspacing="0" border="0" role="presentation" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px">
                         <tr><td style="padding:0;Margin:0;height:0px;width:100%;margin:0px;border-bottom:0px solid #cccccc;background:unset"></td></tr>
                        </table>
                       </td>
                      </tr>
                      <tr>
                       <td align="center" style="padding:0;Margin:0;font-size:0px"><a target="_blank" href="https://tutrastero.com/es/" style="mso-line-height-rule:exactly;text-decoration:underline;color:#5C68E2;font-size:14px"><img title="TuTrastero.com" src="{_ANIV_CS}" alt="TuTrastero.com" width="560" class="adapt-img" style="display:block;font-size:14px;border:0;outline:none;text-decoration:none"></a></td>
                      </tr>
                     </table>
                    </td>
                   </tr>"""

    # Footer (social + legal) — identical across all blueprints
    footer = (
        '<table cellpadding="0" cellspacing="0" align="center" class="es-footer" role="none"'
        ' style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px;'
        'width:100%;table-layout:fixed !important;background-color:transparent;background-repeat:repeat;background-position:center top">'
        '<tr><td align="center" style="padding:0;Margin:0">'
        '<table align="center" cellpadding="0" cellspacing="0" class="es-footer-body"'
        ' style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px;'
        'background-color:transparent;width:640px" role="none">'
        '<tr><td align="left" style="Margin:0;padding-right:20px;padding-left:20px;padding-bottom:20px;padding-top:20px">'
        '<table cellpadding="0" cellspacing="0" width="100%" role="none"'
        ' style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px">'
        '<tr><td align="left" style="padding:0;Margin:0;width:600px">'
        '<table cellpadding="0" cellspacing="0" width="100%" role="presentation"'
        ' style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px">'
        '<tr><td style="padding:0;Margin:0">'
        '<table cellspacing="0" width="100%" border="0" cellpadding="0" class="bxBlockCode" role="presentation"'
        ' style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px">'
        '<tbody class="bxBlockOut"><tr>'
        '<td valign="top" class="bxBlockPadding bxBlockInn bxBlockInnCode" style="padding:0px;Margin:0">'
        '<span style="font-family:Arial;font-size:13px;color:#363636"> S&#237;guenos en las redes: </span><br><br>'
        '<a href="https://www.facebook.com/tutrastero" title="Facebook Tu Trastero"'
        ' style="mso-line-height-rule:exactly;text-decoration:underline;color:#333333;font-size:12px;display:inline-block">'
        '<img alt="Facebook Tu Trastero" height="20" src="https://tutrastero.com/img/icono-facebook-tu-trastero.png"'
        ' width="20" style="display:block;font-size:14px;border:0;outline:none;text-decoration:none"></a>'
        '<a href="https://www.instagram.com/tutrastero_/" title="Instagram Tu Trastero"'
        ' style="mso-line-height-rule:exactly;text-decoration:underline;color:#333333;font-size:12px;display:inline-block">'
        '<img alt="Instagram Tu Trastero" height="20" src="https://tutrastero.com/img/icono-instagram-tu-trastero.png"'
        ' width="20" style="display:block;font-size:14px;border:0;outline:none;text-decoration:none"></a>'
        '<a href="https://twitter.com/tutrastero_" title="Twitter Tu Trastero"'
        ' style="mso-line-height-rule:exactly;text-decoration:underline;color:#333333;font-size:12px;display:inline-block">'
        '<img height="20" src="https://tutrastero.com/img/icono-twitter-tu-trastero.png"'
        ' width="20" alt="Twitter Tu Trastero" style="display:block;font-size:14px;border:0;outline:none;text-decoration:none"></a>'
        '<a href="https://www.pinterest.es/tutrastero/" title="Pinterest Tu Trastero"'
        ' style="mso-line-height-rule:exactly;text-decoration:underline;color:#333333;font-size:12px;display:inline-block">'
        '<img alt="Pinterest Tu Trastero" height="20" src="https://tutrastero.com/img/icono-pinterest-tu-trastero.png"'
        ' width="20" style="display:block;font-size:14px;border:0;outline:none;text-decoration:none"></a>'
        '<a href="https://www.youtube.com/@tutrasterocom" title="Youtube Tu Trastero"'
        ' style="mso-line-height-rule:exactly;text-decoration:underline;color:#333333;font-size:12px;display:inline-block">'
        '<img width="20" alt="Youtube Tu Trastero" height="20" src="https://tutrastero.com/img/icono-youtube-tu-trastero.png"'
        ' style="display:block;font-size:14px;border:0;outline:none;text-decoration:none"></a>'
        '<a href="https://www.linkedin.com/company/tu-trastero/" title="LinkedIn Tu Trastero"'
        ' style="mso-line-height-rule:exactly;text-decoration:underline;color:#333333;font-size:12px;display:inline-block">'
        '<img height="20" src="https://tutrastero.com/img/icono-linkedin-tu-trastero.png"'
        ' width="20" alt="LinkedIn Tu Trastero" style="display:block;font-size:14px;border:0;outline:none;text-decoration:none"></a>'
        '</td></tr></tbody></table></td></tr>'
        '<tr><td align="center" style="padding:20px;Margin:0;font-size:0">'
        '<table border="0" width="100%" height="100%" cellpadding="0" cellspacing="0" role="presentation"'
        ' style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px">'
        '<tr><td style="padding:0;Margin:0;border-bottom:0px solid #cccccc;background:unset;height:0px;width:100%;margin:0px"></td></tr>'
        '</table></td></tr>'
        '<tr><td align="left" style="padding:0;Margin:0;padding-bottom:35px">'
        '<p style="Margin:0;mso-line-height-rule:exactly;font-family:arial,\'helvetica neue\',helvetica,sans-serif;'
        'line-height:13.5px;letter-spacing:0;color:#333333;font-size:9px">'
        'Aviso Legal: Este mensaje y sus archivos adjuntos van dirigidos exclusivamente a su destinatario, '
        'pudiendo contener informaci&#243;n confidencial sometida a secreto profesional. '
        'No est&#225; permitida su comunicaci&#243;n, reproducci&#243;n o distribuci&#243;n sin la autorizaci&#243;n expresa '
        'de TU TRASTERO TU OTRO ESPACIO, S.L.. Si usted no es el destinatario final, por favor el&#237;m&#237;nelo e inf&#243;rmenos por esta v&#237;a.</p>'
        '<p style="Margin:0;mso-line-height-rule:exactly;font-family:arial,\'helvetica neue\',helvetica,sans-serif;'
        'line-height:13.5px;letter-spacing:0;color:#333333;font-size:9px">'
        'Protecci&#243;n de datos: De conformidad con lo dispuesto en las normativas vigentes en protecci&#243;n de datos '
        'personales, el Reglamento (UE) 2016/679 de 27 de abril de 2016 (GDPR) y la Ley Org&#225;nica (ES) 15/1999 de '
        '13 de diciembre (LOPD), le informamos que los datos personales y direcci&#243;n de correo electr&#243;nico, '
        'recabados del propio interesado o de fuentes p&#250;blicas, ser&#225;n tratados bajo la responsabilidad de '
        'TU TRASTERO TU OTRO ESPACIO, S.L. para el env&#237;o de comunicaciones sobre nuestros productos y servicios '
        'y se conservar&#225;n mientras exista un inter&#233;s mutuo para ello. Los datos no ser&#225;n comunicados a terceros, '
        'salvo obligaci&#243;n legal. Le informamos que puede ejercer los derechos de acceso, rectificaci&#243;n, '
        'portabilidad y supresi&#243;n de sus datos y los de limitaci&#243;n y oposici&#243;n a su tratamiento dirigi&#233;ndose '
        'a c/ Reyes Cat&#243;licos 12 - 28108 Alcobendas, Madrid o enviando un mensaje al correo electr&#243;nico a '
        '<a href="mailto:cgi@tutrastero.com" target="_blank"'
        ' style="mso-line-height-rule:exactly;text-decoration:underline;color:#333333;font-size:9px">cgi@tutrastero.com</a>'
        ' o en el enlace m&#225;s abajo. Si considera que el tratamiento no se ajusta a la normativa vigente, '
        'podr&#225; presentar una reclamaci&#243;n ante la autoridad de control en '
        '<a href="http://www.agpd.es" target="_blank"'
        ' style="mso-line-height-rule:exactly;text-decoration:underline;color:#333333;font-size:9px">www.agpd.es</a>.'
        '<br><br>*Consulta condiciones.&nbsp;</p>'
        '</td></tr>'
        '</table></td></tr></table></td></tr>'
        '</table></td></tr></table>'
    )

    copyright_block = (
        '<table cellpadding="0" cellspacing="0" align="center" class="es-content" role="none"'
        ' style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px;'
        'width:100%;table-layout:fixed !important">'
        '<tr><td align="center" style="padding:0;Margin:0">'
        '<table align="center" cellpadding="0" cellspacing="0" bgcolor="#00000000" class="es-content-body"'
        ' style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px;'
        'background-color:transparent;width:600px" role="none">'
        '<tr><td align="left" style="padding:0;Margin:0">'
        '<table cellpadding="0" cellspacing="0" width="100%" role="none"'
        ' style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px">'
        '<tr><td align="center" valign="top" class="es-m-p20" style="padding:0;Margin:0;width:600px">'
        '<table cellpadding="0" cellspacing="0" width="100%" role="presentation"'
        ' style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px">'
        '<tr><td align="left" height="89" class="es-infoblock h-auto" style="padding:0;Margin:0;padding-bottom:35px">'
        '<p style="Margin:0;mso-line-height-rule:exactly;font-family:arial,\'helvetica neue\',helvetica,sans-serif;'
        'line-height:13.5px;letter-spacing:0;color:#333333;font-size:9px">'
        'Este email se ha enviado a &nbsp;EMAIL<br>'
        'Hss recibido recibido este emial porque te has suscrito a alguna de nuestras Newsletter, '
        'puedes cancelar tu suscripci&#243;n en el siguiente enlace:<br><br>'
        'Copyright&#169; 2024 Tu Trastero - Tu Otro Espacio. Todos los derechos reservados.</p>'
        '</td></tr></table></td></tr></table></td></tr></table></td></tr></table>'
    )

    css = """@media only screen and (max-width:600px) {.es-m-p0r { padding-right:0px!important } .es-m-p20 { padding:20px!important } .es-p-default { } *[class="gmail-fix"] { display:none!important } p, a { line-height:150%!important } h1, h1 a { line-height:120%!important } h2, h2 a { line-height:120%!important } h3, h3 a { line-height:120%!important } h4, h4 a { line-height:120%!important } h5, h5 a { line-height:120%!important } h6, h6 a { line-height:120%!important } .es-header-body p { } .es-content-body p { } .es-footer-body p { } .es-infoblock p { } h1 { font-size:36px!important; text-align:left } h2 { font-size:26px!important; text-align:left } h3 { font-size:20px!important; text-align:left } h4 { font-size:24px!important; text-align:left } h5 { font-size:20px!important; text-align:left } h6 { font-size:16px!important; text-align:left } .es-header-body h1 a, .es-content-body h1 a, .es-footer-body h1 a { font-size:36px!important } .es-header-body h2 a, .es-content-body h2 a, .es-footer-body h2 a { font-size:26px!important } .es-header-body h3 a, .es-content-body h3 a, .es-footer-body h3 a { font-size:20px!important } .es-header-body h4 a, .es-content-body h4 a, .es-footer-body h4 a { font-size:24px!important } .es-header-body h5 a, .es-content-body h5 a, .es-footer-body h5 a { font-size:20px!important } .es-header-body h6 a, .es-content-body h6 a, .es-footer-body h6 a { font-size:16px!important } .es-menu td a { font-size:12px!important } .es-header-body p, .es-header-body a { font-size:14px!important } .es-content-body p, .es-content-body a { font-size:14px!important } .es-footer-body p, .es-footer-body a { font-size:14px!important } .es-infoblock p, .es-infoblock a { font-size:12px!important } .es-m-txt-c, .es-m-txt-c h1, .es-m-txt-c h2, .es-m-txt-c h3, .es-m-txt-c h4, .es-m-txt-c h5, .es-m-txt-c h6 { text-align:center!important } .es-m-txt-r, .es-m-txt-r h1, .es-m-txt-r h2, .es-m-txt-r h3, .es-m-txt-r h4, .es-m-txt-r h5, .es-m-txt-r h6 { text-align:right!important } .es-m-txt-j, .es-m-txt-j h1, .es-m-txt-j h2, .es-m-txt-j h3, .es-m-txt-j h4, .es-m-txt-j h5, .es-m-txt-j h6 { text-align:justify!important } .es-m-txt-l, .es-m-txt-l h1, .es-m-txt-l h2, .es-m-txt-l h3, .es-m-txt-l h4, .es-m-txt-l h5, .es-m-txt-l h6 { text-align:left!important } .es-m-txt-r img, .es-m-txt-c img, .es-m-txt-l img { display:inline!important } .es-m-txt-r .rollover:hover .rollover-second, .es-m-txt-c .rollover:hover .rollover-second, .es-m-txt-l .rollover:hover .rollover-second { display:inline!important } .es-m-txt-r .rollover span, .es-m-txt-c .rollover span, .es-m-txt-l .rollover span { line-height:0!important; font-size:0!important; display:block } .es-spacer { display:inline-table } a.es-button, button.es-button { font-size:20px!important; padding:10px 20px 10px 20px!important; line-height:120%!important } a.es-button, button.es-button, .es-button-border { display:inline-block!important } .es-m-fw, .es-m-fw.es-fw, .es-m-fw .es-button { display:block!important } .es-m-il, .es-m-il .es-button, .es-social, .es-social td, .es-menu { display:inline-block!important } .es-adaptive table, .es-left, .es-right { width:100%!important } .es-content table, .es-header table, .es-footer table, .es-content, .es-footer, .es-header { width:100%!important; max-width:600px!important } .adapt-img { width:100%!important; height:auto!important } .es-mobile-hidden, .es-hidden { display:none!important } .es-desk-hidden { width:auto!important; overflow:visible!important; float:none!important; max-height:inherit!important; line-height:inherit!important } tr.es-desk-hidden { display:table-row!important } table.es-desk-hidden { display:table!important } td.es-desk-menu-hidden { display:table-cell!important } .es-menu td { width:1%!important } table.es-table-not-adapt, .esd-block-html table { width:auto!important } .h-auto { height:auto!important } .es-text-ltr .es-text-mobile-size-16, .es-text-ltr .es-text-mobile-size-16 * { font-size:16px!important; line-height:150%!important } .es-text-ltr .es-text-mobile-size-18, .es-text-ltr .es-text-mobile-size-18 * { font-size:18px!important; line-height:150%!important } .es-text-6340 .es-text-mobile-size-18, .es-text-6340 .es-text-mobile-size-18 * { font-size:18px!important; line-height:150%!important } }
@media screen and (max-width:384px) {.mail-message-content { width:414px!important } }"""

    html = f"""<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html dir="ltr" xmlns="http://www.w3.org/1999/xhtml" xmlns:o="urn:schemas-microsoft-com:office:office" lang="es">
 <head>
  <meta charset="UTF-8">
  <meta content="width=device-width, initial-scale=1" name="viewport">
  <meta name="x-apple-disable-message-reformatting">
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <meta content="telephone=no" name="format-detection">
  <title>{title}</title><!--[if (mso 16)]>
    <style type="text/css">
    a {{text-decoration: none;}}
    </style>
    <![endif]--><!--[if gte mso 9]><style>sup {{ font-size: 100% !important; }}</style><![endif]--><!--[if gte mso 9]>
<noscript>
         <xml>
           <o:OfficeDocumentSettings>
           <o:AllowPNG></o:AllowPNG>
           <o:PixelsPerInch>96</o:PixelsPerInch>
           </o:OfficeDocumentSettings>
         </xml>
      </noscript>
<![endif]--><!--[if mso]><xml>
    <w:WordDocument xmlns:w="urn:schemas-microsoft-com:office:word">
      <w:DontUseAdvancedTypographyReadingMail/>
    </w:WordDocument>
    </xml><![endif]-->
  <style type="text/css">
.rollover:hover .rollover-first {{max-height:0px!important;display:none!important}}
.rollover:hover .rollover-second {{max-height:none!important;display:block!important}}
.rollover span {{font-size:0px}}
u + .body img ~ div div {{display:none}}
#outlook a {{padding:0}}
span.MsoHyperlink,span.MsoHyperlinkFollowed {{color:inherit;mso-style-priority:99}}
a.es-button {{mso-style-priority:100!important;text-decoration:none!important}}
a[x-apple-data-detectors],#MessageViewBody a {{color:inherit!important;text-decoration:none!important;font-size:inherit!important;font-family:inherit!important;font-weight:inherit!important;line-height:inherit!important}}
.es-desk-hidden {{display:none;float:left;overflow:hidden;width:0;max-height:0;line-height:0;mso-hide:all}}
{css}
  </style>
 </head>
 <body class="body" style="width:100%;height:100%;-webkit-text-size-adjust:100%;-ms-text-size-adjust:100%;padding:0;Margin:0">
  <div dir="ltr" class="es-wrapper-color" lang="es" style="background-color:#FFFFFF"><!--[if gte mso 9]>
			<v:background xmlns:v="urn:schemas-microsoft-com:vml" fill="t">
				<v:fill type="tile" color="#fff" origin="0.5, 0" position="0.5, 0"></v:fill>
			</v:background>
		<![endif]-->
   <table width="100%" cellspacing="0" cellpadding="0" class="es-wrapper" role="none" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px;padding:0;Margin:0;width:100%;height:100%;background-repeat:repeat;background-position:center top;background-color:#FFFFFF">
     <tr>
      <td valign="top" style="padding:0;Margin:0">
       <table cellpadding="0" cellspacing="0" align="center" class="es-header" role="none" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px;width:100%;table-layout:fixed !important;background-color:transparent;background-repeat:repeat;background-position:center top">
         <tr>
          <td align="center" style="padding:0;Margin:0">
           <table bgcolor="#ffffff" align="center" cellpadding="0" cellspacing="0" class="es-header-body" role="none" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px;background-color:transparent;width:600px">
             <tr>
              <td align="left" style="Margin:0;padding-top:10px;padding-right:20px;padding-bottom:10px;padding-left:20px">
               <table cellpadding="0" cellspacing="0" width="100%" role="none" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px">
                 <tr>
                  <td valign="top" align="center" class="es-m-p0r" style="padding:0;Margin:0;width:560px">
                   <table cellpadding="0" cellspacing="0" width="100%" role="presentation" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px">
                     <tr>
                      <td align="center" style="padding:0;Margin:0;padding-bottom:0px;font-size:0px"><a target="_blank" href="https://tutrastero.com/es/" style="mso-line-height-rule:exactly;text-decoration:underline;color:#666666;font-size:14px"><img src="{_LOGO}" alt="TuTrastero.com" title="TuTrastero.com" width="560" class="adapt-img" style="display:block;font-size:14px;border:0;outline:none;text-decoration:none"></a></td>
                     </tr>
                   </table></td>
                 </tr>
               </table></td>
             </tr>
           </table></td>
         </tr>
       </table>
       <table cellpadding="0" cellspacing="0" align="center" class="es-content" role="none" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px;width:100%;table-layout:fixed !important">
         <tr>
          <td align="center" style="padding:0;Margin:0">
           <table bgcolor="#ffffff" align="center" cellpadding="0" cellspacing="0" class="es-content-body" role="none" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px;background-color:#FFFFFF;width:600px">
             <tr>
              <td align="left" {banner_td_attr}>
               <table cellpadding="0" cellspacing="0" width="100%" role="none" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px">
                 <tr>
                  <td align="center" valign="top" style="padding:0;Margin:0;width:580px">
                   <table cellpadding="0" cellspacing="0" width="100%" role="presentation" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px">
                     <tr>
                      <td align="center" style="padding:0;Margin:0;padding-top:10px;padding-bottom:10px;font-size:0px">{banner_img}</td>
                     </tr>
                   </table></td>
                 </tr>
               </table></td>
             </tr>
           </table></td>
         </tr>
       </table>
       <table cellpadding="0" cellspacing="0" align="center" class="es-content" role="none" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px;width:100%;table-layout:fixed !important">
         <tr class="es-visible-simple-html-only">
          <td align="center" class="es-stripe-html" style="padding:0;Margin:0">
           <table bgcolor="#ffffff" align="center" cellpadding="0" cellspacing="0" class="es-content-body" role="none" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px;background-color:#FFFFFF;width:600px">
             <tr>
              <td align="left" style="padding:0;Margin:0;padding-right:20px;padding-bottom:10px;padding-left:20px">
               <table cellpadding="0" cellspacing="0" width="100%" role="none" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px">
                 <tr>
                  <td align="left" style="padding:0;Margin:0;width:560px">
                   <table cellpadding="0" cellspacing="0" width="100%" role="presentation" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px">
                     <tr>
                      <td {body_cell_attr}>{body_html}</td>
                     </tr>
                   </table></td>
                 </tr>
               </table></td>
             </tr>
             <tr></tr>
             <tr>
              <td align="left" style="Margin:0;padding-right:20px;padding-bottom:10px;padding-left:20px;padding-top:15px">
               <table cellpadding="0" cellspacing="0" width="100%" role="none" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px">
                 <tr>
                  <td align="left" style="padding:0;Margin:0;width:560px">
                   <table cellpadding="0" cellspacing="0" width="100%" role="presentation" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px">
                     {cta_block}
                     {crosssell_block}
                   </table></td>
                 </tr>
               </table></td>
             </tr>
           </table></td>
         </tr>
       </table>
       {footer}
       {copyright_block}
      </td>
     </tr>
   </table>
  </div>
 </body>
</html>"""
    return html


# ─────────────────────────────────────────────────────────────────────────────
# Per-category template functions
# ─────────────────────────────────────────────────────────────────────────────

def ticket_email(nombre: str, lead_id: str) -> str:
    """Generic humano/ticket — bot_humano.py and Otros."""
    n = nombre or "cliente"
    body = (
        f'<p {_P}>Estimado/a {n}<br><br></p>'
        f'<p {_PT}>Hemos recibido su correo y se ha generado el siguiente n&#250;mero de ticket '
        f'<strong class="es-text-mobile-size-18" style="font-size:18px">#{lead_id}</strong>'
        f'<span style="line-height:200%">.<br><br>'
        f'A continuaci&#243;n uno de nuestros gestores se comunicar&#225; con usted para brindarle una atenci&#243;n personalizada. '
        f'Agradecemos su confianza.</span></p>'
    )
    return build("CGI OtrosGen&#233;rico - tutrastero", BANNER_TICKET, body, is_ticket=True)


def cambio_trastero_email(nombre: str, lead_id: str) -> str:
    n = nombre or "cliente"
    body = (
        f'<p {_P}>Estimado/a {n}<br><br></p>'
        f'<p {_PT}>Hemos recibido su solicitud de cambio de trastero y se ha generado el siguiente n&#250;mero de ticket '
        f'<strong class="es-text-mobile-size-18" style="font-size:18px"> #{lead_id}</strong>'
        f'<span style="line-height:200%">.<br><br>'
        f'A continuaci&#243;n uno de nuestros gestores se comunicar&#225; con usted para brindarle una atenci&#243;n personalizada. '
        f'Agradecemos su confianza.</span></p>'
    )
    return build("CGI OtrosGen&#233;rico - tutrastero", BANNER_TICKET, body, is_ticket=True)


def resena_ticket_email(nombre: str, lead_id: str) -> str:
    n = nombre or "cliente"
    body = (
        f'<p {_P}>Estimado/a {n} <br><br></p>'
        f'<p {_PT}>Gracias por compartir su experiencia con nosotros. Para una mejor gesti&#243;n de su caso '
        f'hemos generado el siguiente n&#250;mero de ticket '
        f'<strong class="es-text-mobile-size-18" style="font-size:18px">#{lead_id}</strong>'
        f'<span style="line-height:200%">.<br><br>'
        f'A continuaci&#243;n uno de nuestros gestores se comunicar&#225; con usted para brindarle una atenci&#243;n personalizada. '
        f'Agradecemos su confianza.</span></p>'
    )
    return build("CGI OtrosGen&#233;rico - tutrastero", BANNER_TICKET, body, is_ticket=True)


def otros_ticket_email(nombre: str, lead_id: str) -> str:
    n = nombre or "cliente"
    body = (
        f'<p {_P}>Estimado/a {n}<br><br></p>'
        f'<p {_PT}>Hemos recibido su consulta y se ha generado el siguiente n&#250;mero de ticket '
        f'<strong class="es-text-mobile-size-18" style="font-size:18px">#{lead_id}</strong>'
        f'<span style="line-height:200%">.<br><br>'
        f'A continuaci&#243;n uno de nuestros gestores se comunicar&#225; con usted para brindarle una atenci&#243;n personalizada. '
        f'Agradecemos su confianza.</span></p>'
    )
    return build("CGI OtrosGen&#233;rico - tutrastero", BANNER_TICKET, body, is_ticket=True)


def foto_salida_ticket_email(nombre: str, lead_id: str) -> str:
    n = nombre or "cliente"
    body = (
        f'<p {_P}>Estimado/a {n}<br><br></p>'
        f'<p {_PT}>Hemos recibido su requerimiento y se ha generado el siguiente n&#250;mero de ticket '
        f'<strong class="es-text-mobile-size-18" style="font-size:18px">#{lead_id} </strong>'
        f'<span style="line-height:200%">.<br><br>'
        f'A continuaci&#243;n uno de nuestros gestores se comunicar&#225; con usted para brindarle una atenci&#243;n personalizada. '
        f'Agradecemos su confianza.</span></p>'
    )
    return build("CGI OtrosGen&#233;rico - tutrastero", BANNER_TICKET, body, is_ticket=True)


def area_cliente_email(nombre: str) -> str:
    n = nombre or "cliente"
    body = (
        f'<p {_P}>Estimado/a {n}</p>'
        f'<p {_P}><br></p>'
        f'<p {_P}>Hemos recibido su solicitud correctamente.</p>'
        f'<p {_P}><br></p>'
        f'<p {_P}>Para continuar, por favor,&nbsp; '
        f'<strong style="font-weight:700 !important">acceda a su &#193;rea de Cliente a trav&#233;s del siguiente bot&#243;n</strong>. '
        f'Desde all&#237; podr&#225; finalizar la gesti&#243;n.</p>'
    )
    btn = dark_btn("https://administracion.tutrastero.com/validate-client", "&#193;rea de cliente")
    after = (
        f'<p {_P}>Si usted no ha realizado esta solicitud o tiene problemas para acceder, '
        f'por favor, contacte con su asesor comercial en el 900 902 791.</p>'
    )
    return build("CGI &#193;rea Cliente - tutrastero", BANNER_AREA_CLI, body, btn, after)


def mudanza_email(nombre: str) -> str:
    n = nombre or "cliente"
    body = (
        f'<p {_P}>Estimado/a {n}</p>'
        f'<p {_P}><br></p>'
        f'<p {_P}>Hemos recibido su consulta y le agradecemos su inter&#233;s en nuestros servicios.</p>'
        f'<p {_P}><br></p>'
        f'<p {_P}>Descubra nuestro<strong>&nbsp;servicio de mudanzas nacionales en toda Espa&#241;a&nbsp;</strong>y'
        f'<strong>&nbsp;locales</strong>&nbsp;a&nbsp;<strong>particulares&nbsp;</strong>y&nbsp;<strong>oficinas</strong>. '
        f'Un servicio completo de embalaje profesional y transporte con nuestras&nbsp;<strong>cajas mudanza</strong>&nbsp;y'
        f'<strong>&nbsp;material de embalaje</strong>&nbsp;s&#250;per resistentes.</p>'
    )
    btn = light_btn(_MUDANZA_URL, "&#161;Solicite su mudanza aqu&#237;!")
    return build("CGI Mudanza - tutrastero", BANNER_MUDANZA_IMG, body, btn)


def materiales_email(nombre: str) -> str:
    n = nombre or "cliente"
    body = (
        f'<p {_P}>Estimado/a {n}<br><br></p>'
        f'<p {_P}>Gracias por comunicarse con nosotros.</p>'
        f'<p {_P}><br></p>'
        f'<p {_P}>Descubra el top ventas de las&nbsp;<strong>cajas de cart&#243;n</strong>&nbsp;para mudanzas de gran&nbsp;'
        f'<strong>calidad</strong>,&nbsp;<strong>sostenibles</strong>, al&nbsp;<strong>mejor precio</strong>&nbsp;y de&nbsp;'
        f'<strong>varios tama&#241;os</strong>.</p>'
        f'<p {_P}><br></p>'
        f'<p {_P}>Descubra el top ventas de&nbsp;<strong>material de embalaje</strong>&nbsp;necesario para embalar '
        f'y transportar sus cosas con total protecci&#243;n.</p>'
        f'<p {_P}><br></p>'
        f'<p {_P}>Descubra todos los&nbsp;<strong>accesorios</strong>&nbsp;necesarios&nbsp;<strong>para embalar</strong>, '
        f'transportar&nbsp;<strong>y almacenar</strong> sus cosas como un profesional.</p>'
        f'<p {_P}><br></p>'
        f'<p {_P}>Consiga todo esto y m&#225;s en nuestra tienda virtual.</p>'
    )
    btn = light_btn("https://www.tucaja.com/", "&#161;Compre aqu&#237;!")
    return build("CGI Materiales Embalaje - tutrastero", BANNER_MUDANZA_IMG, body, btn)


def moroso_email(nombre: str) -> str:
    n = nombre or "cliente"
    body = (
        f'<p {_P}>Estimado/a {n}</p>'
        f'<p {_P}><br></p>'
        f'<p {_PL}>Le informamos de que, al constar una factura pendiente, su acceso '
        f'<strong>quedar&#225; inhabilitado temporalmente</strong>.</p>'
        f'<p {_PL}><br></p>'
        f'<p {_PL}>Entendemos que puede tratarse de un descuido administrativo, pero para evitar la interrupci&#243;n '
        f'del servicio y gastos de gesti&#243;n innecesarios, es necesario que '
        f'<strong>regularice su situaci&#243;n lo antes posible</strong>.</p>'
        f'<p {_PL}><br></p>'
        f'<p {_PL}>Puede realizar el pago de forma inmediata y segura entrando en su <strong>&#193;rea de Cliente</strong>:</p>'
        f'<p {_PL}><strong><br></strong></p>'
    )
    btn = dark_btn("https://administracion.tutrastero.com/validate-client", "&#193;rea de Cliente")
    after = (
        f'<p {_PL}>Quedamos a su disposici&#243;n.</p>'
        f'<p {_PL}><br></p>'
        f'<p {_PL}>Atentamente,</p>'
        f'<p {_PL}><br></p>'
        f'<p {_PL}><strong>El equipo de Tu Trastero.</strong></p>'
        f'<p {_PL}><strong><br></strong></p>'
        f'<p {_PL}><strong> </strong><em>Nota: Si usted ya ha realizado la gesti&#243;n o el pago en las &#250;ltimas horas, '
        f'por favor, haga caso omiso a este mensaje; el sistema se actualizar&#225; en breve.</em><strong> </strong></p>'
    )
    return build("CGI Moroso - tutrastero", BANNER_MOROSO, body, btn, after)


def desestima_email(nombre: str) -> str:
    n = nombre or "cliente"
    body = (
        f'<p {_P}>Estimado/a {n}</p>'
        f'<p {_P}><br></p>'
        f'<p {_PL}>Gracias por su inter&#233;s en <strong>Tu Trastero&#174;</strong>.</p>'
        f'<p {_PL}><br></p>'
        f'<p {_PL}>Entendemos que los planes pueden cambiar, por lo que simplemente queremos recordarle '
        f'que seguimos a su disposici&#243;n.</p>'
        f'<p {_PL}><br></p>'
        f'<p {_PL}>Si en el futuro decide retomar su gesti&#243;n, puede <strong>reservar o contratar su trastero</strong> '
        f'c&#243;modamente desde nuestra web:</p>'
    )
    _reservar_url = (
        "https://administracion.tutrastero.com/form/contratacion-online"
        "?utm_campaign=Contrataci%C3%B3n+Online&utm_medium=bitly"
        "&utm_source=Web+%3E+Servicios+Online+%3E+Reservar+Tu+Trastero"
    )
    btn = dark_btn(_reservar_url, "Retomar mi contrataci&#243;n")
    after = (
        f'<p {_PL}>Un cordial saludo,</p>'
        f'<p {_PL}><br></p>'
        f'<p {_PL}><strong>El equipo de Tu Trastero&#174;</strong></p>'
    )
    return build("CGI Desestima Oferta - tutrastero", BANNER_DESESTIMA, body, btn, after)


# ── Área General CTA emails ───────────────────────────────────────────────────

def agendar_visita_email(nombre: str) -> str:
    n = nombre or "cliente"
    body = (
        f'<p {_P}>Estimado/a {n}</p>'
        f'<p {_P}><br></p>'
        f'<p {_P}>Gracias por su inter&#233;s. Para facilitar la coordinaci&#243;n de su visita, le invitamos a usar '
        f'nuestro sistema de reservas online. En &#233;l podr&#225; seleccionar el '
        f'<strong>centro de su preferencia</strong>, as&#237; como la<strong> fecha y hora</strong> que mejor le convengan.</p>'
        f'<p {_P}><br></p>'
        f'<p {_P}>El proceso es r&#225;pido y sencillo. Solo tiene que hacer clic en el siguiente bot&#243;n para comenzar:</p>'
    )
    btn = dark_btn("https://tutrastero.com/es/agendar-visita/", "Agendar mi visita ahora")
    return build("CGI Agendar Visita - tutrastero", BANNER_AGENDAR, body, btn)


def reservar_trastero_email(nombre: str) -> str:
    n = nombre or "cliente"
    body = (
        f'<p {_P}>Estimado/a {n}</p>'
        f'<p {_P}><br></p>'
        f'<p {_P}>Gracias por su inter&#233;s en Tu Trastero. Est&#225; a un solo paso de tener el trastero perfecto para usted.</p>'
        f'<p {_P}><br></p>'
        f'<p {_P}>Le invitamos a completar su reserva a trav&#233;s de nuestro portal seguro. Al hacerlo, podr&#225; '
        f'<strong>garantizar la disponibilidad inmediata del espacio, el tama&#241;o y las fechas</strong> que necesita.</p>'
        f'<p {_P}><br></p>'
        f'<p {_P}>Para finalizar el proceso, por favor, haga clic en el siguiente bot&#243;n:</p>'
    )
    _url = (
        "https://administracion.tutrastero.com/form/contratacion-online"
        "?utm_campaign=Contrataci%C3%B3n+Online&utm_medium=bitly"
        "&utm_source=Web+%3E+Servicios+Online+%3E+Reservar+Tu+Trastero"
    )
    btn = dark_btn(_url, "Reservar y asegurar mi trastero")
    return build("CGI Reservar Tu Trastero - tutrastero", BANNER_RESERVAR, body, btn)


def notificar_incidencia_email(nombre: str) -> str:
    n = nombre or "cliente"
    body = (
        f'<p {_P}>Estimado/a {n}</p>'
        f'<p {_P}><br></p>'
        f'<p {_P}>En Tu Trastero&#174;, su tranquilidad es lo m&#225;s importante. Entendemos que a veces pueden surgir '
        f'imprevistos y queremos que sepa que estamos aqu&#237; para ayudar a solucionarlos de la forma m&#225;s r&#225;pida '
        f'y eficaz posible.</p>'
        f'<p {_P}><br></p>'
        f'<p {_P}>Para ello, hemos creado un portal de soporte directo. Si tiene cualquier incidencia, puede '
        f'gestionarla f&#225;cilmente desde un &#250;nico lugar.</p>'
        f'<p {_P}><br></p>'
        f'<p {_P}>Haga clic en el siguiente bot&#243;n para abrir un caso y nuestro equipo se pondr&#225; en marcha:</p>'
    )
    btn = dark_btn("https://tutrastero.com/es/servicios-online/gestion-incidencias/", "Reportar incidencia")
    return build("CGI Notificar Incidencia - tutrastero", BANNER_INCIDENCIA, body, btn)


def autorizar_terceros_email(nombre: str) -> str:
    n = nombre or "cliente"
    body = (
        f'<p {_P}>Estimado/a {n}</p>'
        f'<p {_P}><br></p>'
        f'<p {_PL}>En Tu Trastero&#174;, su seguridad y control son nuestra m&#225;xima prioridad. Por eso, le recordamos '
        f'que tiene control total sobre qui&#233;n puede acceder a su trastero.</p>'
        f'<p {_PL}><br></p>'
        f'<p {_PL}>A trav&#233;s del siguiente bot&#243;n, puede <strong>autorizar a las personas </strong>para entrar a su '
        f'm&#243;dulo de Tu Trastero&#174;, tal como lo har&#237;a usted mismo.</p>'
    )
    btn = dark_btn("https://tutrastero.com/es/servicios-online/autorizacion-de-terceros/", "Gestionar mis accesos")
    return build("CGI Autorizar Terceros - tutrastero", BANNER_AUTORIZAR, body, btn)


def actualizar_datos_email(nombre: str) -> str:
    n = nombre or "cliente"
    body = (
        f'<p {_P}>Estimado/a {n}</p>'
        f'<p {_P}><br></p>'
        f'<p {_P}>Hemos recibido su solicitud para actualizar los datos de su contrato.</p>'
        f'<p {_P}><br></p>'
        f'<p {_P}>Para continuar, por favor, pulse el siguiente bot&#243;n. Le llevar&#225; directamente al formulario '
        f'para que pueda realizar los cambios de forma segura.</p>'
    )
    btn = dark_btn("https://tutrastero.com/es/servicios-online/actualizar/", "Actualizar mis datos")
    after = (
        f'<p {_P}>Una vez dentro, podr&#225; modificar su tel&#233;fono, email, m&#233;todo de pago y m&#225;s.</p>'
        f'<p {_P}><br></p>'
        f'<p {_P}>Si no ha solicitado esta acci&#243;n o encuentra alguna dificultad, por favor, contacte con su asesor comercial.</p>'
    )
    return build("CGI Actualizar Datos - tutrastero", BANNER_ACTUALIZAR, body, btn, after)


def hacer_inventario_email(nombre: str) -> str:
    n = nombre or "cliente"
    body = (
        f'<p {_P}>Estimado/a {n}</p>'
        f'<p {_P}><br></p>'
        f'<p {_PL}>Gracias por contactar con el equipo de Tu Trastero&#174;.</p>'
        f'<p {_PL}><br></p>'
        f'<p {_P}>En respuesta a su consulta, la mejor manera de llevar un control detallado de tus pertenencias '
        f'es utilizando nuestra herramienta de <strong>inventario digital</strong>.</p>'
        f'<p {_P}><br></p>'
        f'<p {_P}>Con ella, podr&#225;s <strong>crear un inventario de todas las pertenencias que guardar&#225;s en '
        f'Tu Trastero&#174;</strong> y estar siempre organizado.</p>'
    )
    btn = dark_btn("https://tutrastero.com/es/servicios-online/inventario/", "Hacer inventario")
    return build("CGI Hacer Inventario - tutrastero", BANNER_INVENTARIO, body, btn)


def hacer_valoracion_email(nombre: str) -> str:
    n = nombre or "cliente"
    body = (
        f'<p {_P}>Estimado/a {n}</p>'
        f'<p {_P}><br></p>'
        f'<p {_P}>Gracias por contactarnos.</p>'
        f'<p {_PL}><br></p>'
        f'<p {_P}>En respuesta a su consulta, le confirmamos que la forma m&#225;s sencilla de registrar el valor '
        f'de tus pertenencias es a trav&#233;s de nuestra herramienta de inventario online.</p>'
        f'<p {_P}><br></p>'
        f'<p {_P}>Dentro de ella, tiene la opci&#243;n de <strong>indicar el valor de cada una de las pertenencias '
        f'que guarda en su m&#243;dulo.</strong> Esto es fundamental para tener un control total y asegurarte de '
        f'que tu cobertura de seguro es la adecuada.</p>'
        f'<p {_P}><br></p>'
        f'<p {_P}>Puedes acceder directamente y empezar ahora mismo desde el siguiente bot&#243;n:</p>'
    )
    btn = dark_btn("https://tutrastero.com/es/servicios-online/declaracion-de-valor/", "Indicar el valor de mis bienes")
    return build("CGI Hacer Valoraci&#243;n - tutrastero", BANNER_VALORACION, body, btn)


def presupuesto_email(nombre: str) -> str:
    n = nombre or "cliente"
    body = (
        f'<p {_P}>Estimado/a {n}</p>'
        f'<p {_P}><br></p>'
        f'<p {_P}>Gracias por su inter&#233;s en Tu Trastero&#174;.</p>'
        f'<p {_P}><br></p>'
        f'<p {_P}>Consiga su presupuesto a su medida y sin compromiso desde nuestra web, '
        f'haciendo clic en el siguiente bot&#243;n.</p>'
    )
    btn = dark_btn("https://tutrastero.com/es/solicitud-de-presupuesto/", "Quiero mi presupuesto")
    return build("CGI Presupuesto - tutrastero", BANNER_PRESUPUESTO, body, btn)
