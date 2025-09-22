# build_ga_pdfs.ps1
# Build PDFs for Grand Archive decks listed in a text file.
# Options used on every build: --quality 100 --crop 2.5mm --load_offset
# Auto-includes --double_sided_dir_path "<deck>\double_sided" when that folder exists.

$deckRoot = 'E:\Card Game Proxies\Grand Archive\Decklists'     # root that contains each deck folder
$listPath = Join-Path $deckRoot 'ls.txt'                       # text file listing deck folder names (one per line)
$backDir  = 'E:\Card Game Proxies\Grand Archive\Card Back'     # backs directory
$pdfOut   = 'E:\Card Game Proxies\Grand Archive\PDFs'          # output PDFs folder
$python   = 'py'                                               # python launcher (use full path if needed)

# Ensure output exists
New-Item -ItemType Directory -Path $pdfOut -Force | Out-Null

if (-not (Test-Path -LiteralPath $listPath)) {
  Write-Error "List file not found: $listPath"
  exit 1
}

if (-not (Test-Path -LiteralPath $backDir)) {
  Write-Error "Backs directory not found: $backDir"
  exit 1
}

$built = 0; $skipped = 0; $failed = 0

# Read list (ignore blank lines)
$Decks = Get-Content -LiteralPath $listPath | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne '' }

foreach ($name in $Decks) {
  $front = Join-Path $deckRoot $name

  if (-not (Test-Path -LiteralPath $front)) {
    Write-Warning "Front dir not found: $front  (skipping)"
    $skipped++
    continue
  }

  $doubleSided = Join-Path $front 'double_sided'
  $hasDouble   = Test-Path -LiteralPath $doubleSided

  $outPdf = Join-Path $pdfOut ($name + '.pdf')

  Write-Host "Building:`t$name"
  $args = @(
    'create_pdf.py'
    ,'--front_dir_path', "$front"
    ,'--back_dir_path',  "$backDir"
    ,'--output_path',    "$outPdf"
    ,'--name',           "$name"
    ,'--quality',        '100'
    ,'--crop',           '2.5mm'
    ,'--load_offset'
  )

  if ($hasDouble) {
    $args += @('--double_sided_dir_path', "$doubleSided")
  } elseif ($name -match '(?i)unique front and backs') {
    Write-Warning "Deck marked 'Unique front and backs' but no 'double_sided' folder found: $doubleSided"
  }

  & $python @args
  if ($LASTEXITCODE -ne 0) {
    Write-Warning "Failed:`t$name  (exit $LASTEXITCODE)"
    $failed++
  } else {
    $built++
  }
}

Write-Host "`nDone. Built: $built | Skipped: $skipped | Failed: $failed | Output: $pdfOut"
