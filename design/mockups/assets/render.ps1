$ErrorActionPreference = "Stop"
$mock = Split-Path -Parent $PSScriptRoot
$pagesDir = Join-Path $mock "pages"
$shots = Join-Path $mock "screenshots"
New-Item -ItemType Directory -Force -Path $shots | Out-Null
$chrome = "C:\Program Files\Google\Chrome\Application\chrome.exe"

$pages = @(
  @{ file = "command-center.html"; out = "01-command-center.png"; w = 1600; h = 1380 },
  @{ file = "circuit-detail.html"; out = "02-circuit-detail.png"; w = 1600; h = 1820 },
  @{ file = "alert-queue.html";    out = "03-alert-queue.png";    w = 1600; h = 1260 },
  @{ file = "field-tablet.html";   out = "04-field-tablet.png";   w = 1024; h = 1040; scale = 2 },
  @{ file = "model-health.html";   out = "05-model-health.png";   w = 1600; h = 1900 },
  @{ file = "design-system.html";  out = "06-design-system.png";  w = 1600; h = 3980 },
  @{ file = "index.html";          out = "00-cover.png";          w = 1600; h = 2280 }
)

$only = $args[0]

foreach ($p in $pages) {
  if ($only -and $p.out -notlike "*$only*") { continue }
  $uri = ([System.Uri](Join-Path $pagesDir $p.file)).AbsoluteUri
  $png = Join-Path $shots $p.out
  if (Test-Path $png) { Remove-Item $png }
  $scale = if ($p.scale) { $p.scale } else { 1 }
  $profile = Join-Path ([System.IO.Path]::GetTempPath()) ("nidan-shot-" + [Guid]::NewGuid().ToString("N").Substring(0, 8))
  $chromeArgs = @(
    "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-sandbox",
    "--no-first-run", "--disable-extensions", "--disable-background-networking",
    "--user-data-dir=`"$profile`"",
    "--force-device-scale-factor=$scale",
    "--window-size=$($p.w),$($p.h)",
    "--virtual-time-budget=2000",
    "--screenshot=`"$png`"",
    $uri
  )
  $proc = Start-Process -FilePath $chrome -ArgumentList $chromeArgs -PassThru -WindowStyle Hidden
  $proc | Wait-Process -Timeout 45 -ErrorAction SilentlyContinue
  if (-not $proc.HasExited) { try { $proc.Kill() } catch {} }
  Start-Sleep -Milliseconds 300

  if (Test-Path $png) {
    $len = (Get-Item $png).Length
    Write-Output ("OK   " + $p.out + "  " + [math]::Round($len / 1kb) + " KB")
  } else {
    Write-Output ("FAIL " + $p.out)
  }
  Remove-Item -Recurse -Force $profile -ErrorAction SilentlyContinue
}

