<!DOCTYPE html>
<html>
<head>
<title>File Downloader UI</title>
</head>
<body>
<h1>File Downloader</h1>

<progress value="0" max="100"></progress>

<?php
$file_urls = array('');
$save_to = array('');

for ($i = 0; $i < count($file_urls); $i++) {
  $file_url = $file_urls[$i];
  $save_file_path = $save_to[$i];

  $ch = curl_init();
  curl_setopt($ch, CURLOPT_URL, $file_url);
  curl_setopt($ch, CURLOPT_RETURNTRANSFER, 1);
  curl_setopt($ch, CURLOPT_SSLVERSION,3);

  curl_setopt($ch, CURLOPT_HEADER, true);
  curl_setopt($ch, CURLOPT_NOBODY, true);
  curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
  curl_exec($ch);
  $size = curl_getinfo($ch, CURLINFO_CONTENT_LENGTH_DOWNLOAD);
  curl_close($ch);

  $progress = 0;
  $fp = fopen($save_file_path, 'w');
  $ch = curl_init();
  curl_setopt($ch, CURLOPT_URL, $file_url);
  curl_setopt($ch, CURLOPT_RETURNTRANSFER, 1);
  curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
  curl_setopt($ch, CURLOPT_WRITEFUNCTION, function($curl, $data) use ($fp, &$progress, $size) {
      $bytes = fwrite($fp, $data);
      $progress += $bytes;
      if ($size > 0) {
          $percent = round(($progress / $size) * 100);
          echo "<script>document.querySelector('progress').value = $percent;</script>";
      }
      return $bytes;
  });
  curl_exec($ch);
  fclose($fp);
  curl_close($ch);

  echo "<p>File downloaded successfully: $file_url</p>";
}
?>
</body>
</html>
